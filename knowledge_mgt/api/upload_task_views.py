"""
文档上传任务队列管理API
实现异步文档处理和任务状态管理
"""

import json
import logging
import os
import uuid
import threading
import time
from datetime import datetime
from django.db import connection, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from zhiqing_server.utils.response_code import *
from zhiqing_server.utils.auth_utils import (
    jwt_required, get_user_from_request,
    parse_json_body, validate_required_fields,
    create_error_response, create_success_response
)
from zhiqing_server.utils.db_utils import execute_query_with_params
from knowledge_mgt.utils.document_processor import get_document_processor, get_supported_formats
from knowledge_mgt.utils.vector_store import VectorStore
from knowledge_mgt.utils.text_filter import TextFilter
from knowledge_mgt.models import StopWord, SensitiveWord

# 获取模块日志记录器
logger = logging.getLogger('knowledge_mgt')


def calculate_queue_time_estimates(cursor, pending_count, current_task):
    """计算队列时间估算"""
    try:
        if pending_count == 0:
            return {
                'estimated_wait_time': 0,
                'estimated_completion_time': 0,
                'queue_position': 0,
                'time_per_task': 0
            }
        
        # 获取历史任务的平均处理时间
        cursor.execute("""
            SELECT 
                AVG(TIMESTAMPDIFF(SECOND, started_at, completed_at)) as avg_processing_time,
                COUNT(*) as sample_count
            FROM document_upload_task
            WHERE status = 'completed' 
                AND started_at IS NOT NULL 
                AND completed_at IS NOT NULL
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        
        history_result = cursor.fetchone()
        avg_processing_time = history_result[0] if history_result and history_result[0] else 120  # 默认2分钟
        
        # 如果当前有任务在处理，计算剩余时间
        current_task_remaining = 0
        if current_task and current_task.get('progress', 0) > 0:
            progress = current_task['progress']
            if progress < 100:
                # 根据进度估算剩余时间
                elapsed_time = time.time() - (datetime.strptime(current_task['started_at'], "%Y-%m-%d %H:%M:%S").timestamp() if current_task['started_at'] else time.time())
                current_task_remaining = max(0, (elapsed_time / progress * (100 - progress)) if progress > 0 else 0)
        
        # 计算队列中每个任务的预估时间
        estimated_time_per_task = avg_processing_time
        
        # 计算总等待时间
        total_wait_time = current_task_remaining + (pending_count * estimated_time_per_task)
        
        # 格式化时间显示
        def format_time(seconds):
            if seconds < 60:
                return f"{int(seconds)}秒"
            elif seconds < 3600:
                return f"{int(seconds // 60)}分钟"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}小时{minutes}分钟"
        
        return {
            'estimated_wait_time': format_time(total_wait_time),
            'estimated_completion_time': format_time(total_wait_time + (avg_processing_time if current_task else 0)),
            'queue_position': pending_count,
            'time_per_task': format_time(estimated_time_per_task),
            'current_task_progress': current_task.get('progress', 0) if current_task else 0,
            'current_task_remaining': format_time(current_task_remaining) if current_task_remaining > 0 else "0秒"
        }
        
    except Exception as e:
        logger.error(f"计算时间估算失败: {e}")
        return {
            'estimated_wait_time': "计算中...",
            'estimated_completion_time': "计算中...",
            'queue_position': pending_count,
            'time_per_task': "计算中...",
            'current_task_progress': 0,
            'current_task_remaining': "计算中..."
        }


def calculate_remaining_time(progress, started_at, file_size, chunking_method):
    """计算任务预估剩余时间 - 优化版本，支持前快后慢进度分配"""
    try:
        if not progress or progress <= 0 or not started_at:
            return "计算中..."
        
        if progress >= 100:
            return "即将完成"
        
        # 计算已用时间
        if isinstance(started_at, str):
            started_time = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
        else:
            started_time = started_at
        
        elapsed_seconds = (datetime.now() - started_time).total_seconds()
        
        # 根据文档类型和大小计算基础处理时间
        base_time = calculate_base_processing_time(file_size, chunking_method)
        
        # 应用前快后慢的进度分配算法
        adjusted_progress = apply_progress_distribution(progress)
        
        # 根据调整后的进度计算预估总时间
        if adjusted_progress > 0:
            estimated_total_seconds = elapsed_seconds / (adjusted_progress / 100)
            remaining_seconds = estimated_total_seconds - elapsed_seconds
        else:
            remaining_seconds = base_time
        
        # 预留10%的缓冲时间
        buffer_time = remaining_seconds * 0.1
        final_remaining_seconds = remaining_seconds + buffer_time
        
        # 格式化时间显示
        return format_time_display(final_remaining_seconds)
        
    except Exception as e:
        logger.error(f"计算剩余时间失败: {e}")
        return "计算中..."


def calculate_base_processing_time(file_size, chunking_method):
    """根据文件大小和分块方法计算基础处理时间"""
    try:
        # 基础时间配置（秒）
        base_config = {
            'small': {  # < 50KB
                'size_threshold': 50 * 1024,
                'base_time': 30,
                'size_factor': 0.5
            },
            'medium': {  # 50KB - 500KB
                'size_threshold': 500 * 1024,
                'base_time': 60,
                'size_factor': 1.0
            },
            'large': {  # 500KB - 5MB
                'size_threshold': 5 * 1024 * 1024,
                'base_time': 180,
                'size_factor': 1.5
            },
            'xlarge': {  # > 5MB
                'size_threshold': float('inf'),
                'base_time': 300,
                'size_factor': 2.0
            }
        }
        
        # 确定文件大小类别
        size_category = None
        for category, config in base_config.items():
            if file_size < config['size_threshold']:
                size_category = category
                break
        
        if not size_category:
            size_category = 'xlarge'
        
        config = base_config[size_category]
        
        # 计算基础时间
        base_time = config['base_time']
        
        # 根据实际文件大小调整
        if size_category == 'small':
            adjusted_time = base_time + (file_size / config['size_threshold']) * 30
        elif size_category == 'medium':
            adjusted_time = base_time + (file_size - 50 * 1024) / (450 * 1024) * 120
        elif size_category == 'large':
            adjusted_time = base_time + (file_size - 500 * 1024) / (4.5 * 1024 * 1024) * 300
        else:  # xlarge
            adjusted_time = base_time + (file_size - 5 * 1024 * 1024) / (10 * 1024 * 1024) * 600
        
        # 应用分块方法调整因子
        method_factors = {
            'token': 1.0,           # 标准分块
            'sentence': 1.1,        # 句子分块，稍慢
            'paragraph': 1.2,       # 段落分块，较慢
            'chapter': 1.5,         # 章节分块，最慢
            'semantic': 1.8,        # 语义分块，需要AI处理
            'recursive': 1.6,       # 递归分块，复杂
            'sliding_window': 1.3,  # 滑动窗口，中等
            'custom_delimiter': 1.1, # 自定义分隔符
            'fixed_length': 1.0     # 固定长度，标准
        }
        
        method_factor = method_factors.get(chunking_method, 1.0)
        final_time = adjusted_time * method_factor
        
        return max(final_time, 30)  # 最少30秒
        
    except Exception as e:
        logger.error(f"计算基础处理时间失败: {e}")
        return 120  # 默认2分钟


def apply_progress_distribution(progress):
    """应用更合理的进度分配算法"""
    try:
        # 新的进度分配：文档处理占80%，其余平分20%
        if progress <= 20:
            # 初始化阶段：20%进度，占5%时间（快速）
            return progress * 0.25
        elif progress <= 80:
            # 文档处理阶段：60%进度，占80%时间（主要耗时）
            return 5 + (progress - 20) * 1.34
        else:
            # 完成阶段：20%进度，占15%时间（中等速度）
            remaining_progress = progress - 80
            return 80 + remaining_progress * 0.75
        
    except Exception as e:
        logger.error(f"应用进度分配失败: {e}")
        return progress  # 如果失败，返回原始进度


def format_time_display(seconds):
    """格式化时间显示"""
    try:
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes}分钟"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}小时{minutes}分钟"
    except Exception as e:
        logger.error(f"格式化时间显示失败: {e}")
        return "计算中..."


def format_file_size(bytes_size):
    """格式化文件大小显示"""
    try:
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size // 1024} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size // (1024 * 1024)} MB"
        else:
            return f"{bytes_size // (1024 * 1024 * 1024)} GB"
    except Exception as e:
        logger.error(f"格式化文件大小失败: {e}")
        return "未知大小"


def get_queue_info_for_task(task_id, user_id):
    """获取任务的队列信息"""
    try:
        with connection.cursor() as cursor:
            # 获取任务在队列中的位置
            cursor.execute("""
                SELECT COUNT(*) as position
                FROM document_upload_task
                WHERE status = 'pending' 
                    AND (
                        (user_id = %s AND created_at <= (
                            SELECT created_at FROM document_upload_task WHERE task_id = %s
                        )) OR
                        (user_id != %s AND created_at < (
                            SELECT created_at FROM document_upload_task WHERE task_id = %s
                        ))
                    )
            """, [user_id, task_id, user_id, task_id])
            
            position_result = cursor.fetchone()
            queue_position = position_result[0] if position_result else 0
            
            # 获取队列统计信息
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count
                FROM document_upload_task
            """)
            
            stats_result = cursor.fetchone()
            pending_count = stats_result[0] if stats_result else 0
            processing_count = stats_result[1] if stats_result else 0
            
            # 计算预估等待时间
            estimated_wait_time = calculate_simple_time_estimate(queue_position, processing_count)
            
            return {
                'queue_position': queue_position + 1,  # 显示从1开始的位置
                'total_pending': pending_count,
                'currently_processing': processing_count,
                'estimated_wait_time': estimated_wait_time,
                'priority': 'high' if queue_position == 0 else 'normal'
            }
            
    except Exception as e:
        logger.error(f"获取队列信息失败: {e}")
        return {
            'queue_position': 1,
            'total_pending': 0,
            'currently_processing': 0,
            'estimated_wait_time': "计算中...",
            'priority': 'normal'
        }


def calculate_simple_time_estimate(queue_position, processing_count):
    """简单的时间估算"""
    try:
        if queue_position == 0:
            return "即将开始"
        
        # 基础估算：每个任务平均2分钟
        base_time_per_task = 120  # 秒
        
        # 如果有正在处理的任务，考虑其剩余时间
        if processing_count > 0:
            # 假设当前任务已完成一半
            current_task_remaining = base_time_per_task * 0.5
        else:
            current_task_remaining = 0
        
        # 计算总等待时间
        total_wait_seconds = current_task_remaining + (queue_position * base_time_per_task)
        
        # 格式化时间显示
        if total_wait_seconds < 60:
            return f"{int(total_wait_seconds)}秒"
        elif total_wait_seconds < 3600:
            minutes = int(total_wait_seconds // 60)
            return f"{minutes}分钟"
        else:
            hours = int(total_wait_seconds // 3600)
            minutes = int((total_wait_seconds % 3600) // 60)
            return f"{hours}小时{minutes}分钟"
            
    except Exception as e:
        logger.error(f"计算时间估算失败: {e}")
        return "计算中..."


# 全局任务处理锁，确保同时只有一个任务在处理
task_processing_lock = threading.Lock()
current_processing_task = None

# 队列状态缓存
queue_status_cache = {
    'data': None,
    'last_update': 0,
    'cache_duration': 5  # 缓存5秒
}

# 任务处理时间基准（秒）
TASK_TIME_BASELINE = {
    'small_file': 30,      # 小文件（<1MB）
    'medium_file': 120,    # 中等文件（1-10MB）
    'large_file': 300,     # 大文件（>10MB）
    'chunking_methods': {
        'token': 1.0,      # 基础分块方法
        'semantic': 1.5,   # 语义分块
        'sliding': 1.2,    # 滑动窗口
        'chapter': 1.8,    # 章节分块
        'custom': 1.3      # 自定义分块
    }
}


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def create_upload_task(request):
    """创建文档上传任务"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        username = user_info.get('user_name')

        # 获取表单数据
        database_id = request.POST.get('database_id')
        chunking_method = request.POST.get('chunking_method', 'token')
        chunk_size = int(request.POST.get('chunk_size', 500))
        similarity_threshold = float(request.POST.get('similarity_threshold', 0.7))
        overlap_size = int(request.POST.get('overlap_size', 100))
        custom_delimiter = request.POST.get('custom_delimiter', '\n\n')
        window_size = int(request.POST.get('window_size', 3))
        step_size = int(request.POST.get('step_size', 1))
        min_chunk_size = int(request.POST.get('min_chunk_size', 50))
        max_chunk_size = int(request.POST.get('max_chunk_size', 2000))
        file = request.FILES.get('file')

        # 验证参数
        if not database_id or not file:
            return create_error_response("缺少必要参数", 400)

        # 验证文件格式
        file_extension = os.path.splitext(file.name)[1].lower()
        supported_formats = get_supported_formats()
        if file_extension not in supported_formats:
            return create_error_response(f"不支持的文件格式: {file_extension}，支持格式: {', '.join(supported_formats)}", 400)

        # 验证文件大小
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size > max_size:
            return create_error_response("文件大小不能超过 50MB", 400)

        # 验证知识库是否存在
        kb_sql = "SELECT id, name FROM knowledge_database WHERE id = %s"
        kb_params = [database_id]
        
        # 普通用户只能访问自己的知识库
        if user_info.get('role_id') != 1:
            kb_sql += " AND user_id = %s"
            kb_params.append(user_id)
        
        kb_result = execute_query_with_params(kb_sql, kb_params)
        if not kb_result:
            return create_error_response('知识库不存在或无权限访问', 404)

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 保存文件
        file_path = os.path.join('media', 'documents', f"{task_id}_{file.name}")
        full_file_path = os.path.join(settings.MEDIA_ROOT, 'documents', f"{task_id}_{file.name}")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
        
        with open(full_file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        file_info = {
            'filename': file.name,
            'file_path': full_file_path,
            'file_size': file.size
        }
        
        # 创建上传任务记录
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO document_upload_task 
                (task_id, user_id, username, database_id, filename, file_path, file_size,
                 chunking_method, chunk_size, similarity_threshold, overlap_size,
                 custom_delimiter, window_size, step_size, min_chunk_size, max_chunk_size,
                 status, progress)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                task_id, user_id, username, database_id, file_info['filename'], 
                file_info['file_path'], file_info['file_size'],
                chunking_method, chunk_size, similarity_threshold, overlap_size,
                custom_delimiter, window_size, step_size, min_chunk_size, max_chunk_size,
                'pending', 0
            ])

        logger.info(f"创建文档上传任务: {task_id}, 文件: {file_info['filename']}")

        # 获取队列位置和时间估算
        queue_info = get_queue_info_for_task(task_id, user_id)
        
        # 启动异步处理任务（当未启用独立队列worker时）
        if os.environ.get('QUEUE_WORKER', '0') != '1':
            threading.Thread(target=process_upload_task, args=(task_id,), daemon=True).start()

        return create_success_response({
            "task_id": task_id,
            "filename": file_info['filename'],
            "status": "pending",
            "queue_info": queue_info
        })

    except Exception as e:
        logger.error(f"创建上传任务失败: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_upload_tasks(request):
    """获取用户的上传任务列表"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')

        # 构建查询SQL
        sql = """
            SELECT t.task_id, t.filename, t.status, t.progress, t.error_message,
                   t.chunk_count, t.created_at, t.updated_at, t.started_at, t.completed_at,
                   k.name as database_name
            FROM document_upload_task t
            LEFT JOIN knowledge_database k ON t.database_id = k.id
        """
        params = []

        # 普通用户只能看自己的任务
        if role_id != 1:
            sql += " WHERE t.user_id = %s"
            params.append(user_id)

        sql += " ORDER BY t.created_at DESC LIMIT 50"

        tasks = execute_query_with_params(sql, params)

        # 格式化时间字段
        for task in tasks:
            for time_field in ['created_at', 'updated_at', 'started_at', 'completed_at']:
                if task[time_field]:
                    task[time_field] = task[time_field].strftime("%Y-%m-%d %H:%M:%S")

        return create_success_response({"tasks": tasks})

    except Exception as e:
        logger.error(f"获取上传任务列表失败: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_task_status(request, task_id):
    """获取特定任务的状态"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')

        # 构建查询SQL
        sql = """
            SELECT task_id, filename, status, progress, error_message, chunk_count,
                   created_at, updated_at, started_at, completed_at, document_id
            FROM document_upload_task t
            WHERE task_id = %s
        """
        params = [task_id]

        # 普通用户只能查看自己的任务
        if role_id != 1:
            sql += " AND user_id = %s"
            params.append(user_id)

        tasks = execute_query_with_params(sql, params)
        if not tasks:
            return create_error_response('任务不存在或无权限访问', 404)

        task = tasks[0]

        # 格式化时间字段
        for time_field in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if task[time_field]:
                task[time_field] = task[time_field].strftime("%Y-%m-%d %H:%M:%S")

        return create_success_response({"task": task})

    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_queue_status(request):
    """获取队列状态（带缓存优化和时间估算）"""
    try:
        current_time = time.time()
        
        # 检查缓存是否有效
        if (queue_status_cache['data'] is not None and 
            current_time - queue_status_cache['last_update'] < queue_status_cache['cache_duration']):
            return create_success_response(queue_status_cache['data'])
        
        with connection.cursor() as cursor:
            # 获取队列统计信息
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count
                FROM document_upload_task
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            
            stats = cursor.fetchone()
            
            # 获取当前处理的任务
            current_task = None
            if current_processing_task:
                cursor.execute("""
                    SELECT task_id, filename, progress, started_at, file_size, chunking_method, 
                           status_message, created_at
                    FROM document_upload_task
                    WHERE task_id = %s
                """, [current_processing_task])
                
                task_row = cursor.fetchone()
                if task_row:
                    # 计算预估剩余时间
                    estimated_remaining_time = calculate_remaining_time(
                        task_row[2],  # progress
                        task_row[3],  # started_at
                        task_row[4],  # file_size
                        task_row[5]   # chunking_method
                    )
                    
                    current_task = {
                        'task_id': task_row[0],
                        'filename': task_row[1],
                        'progress': task_row[2],
                        'started_at': task_row[3].strftime("%Y-%m-%d %H:%M:%S") if task_row[3] else None,
                        'file_size': task_row[4],
                        'chunking_method': task_row[5],
                        'status_message': task_row[6],
                        'created_at': task_row[7].strftime("%Y-%m-%d %H:%M:%S") if task_row[7] else None,
                        'estimated_remaining_time': estimated_remaining_time,
                        'file_size_formatted': format_file_size(task_row[4])
                    }
            
            # 获取待处理任务队列（按优先级排序）
            cursor.execute("""
                SELECT task_id, filename, file_size, chunking_method, created_at, 
                       user_id, username
                FROM document_upload_task
                WHERE status = 'pending'
                ORDER BY 
                    CASE 
                        WHEN user_id = %s THEN 1  -- 当前用户任务优先
                        ELSE 2
                    END,
                    created_at ASC  -- 按创建时间排序
                LIMIT 10
            """, [request.user.id if hasattr(request, 'user') else 0])
            
            pending_tasks = []
            for row in cursor.fetchall():
                pending_tasks.append({
                    'task_id': row[0],
                    'filename': row[1],
                    'file_size': row[2],
                    'chunking_method': row[3],
                    'created_at': row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None,
                    'user_id': row[5],
                    'username': row[6],
                    'priority': 'high' if row[5] == (request.user.id if hasattr(request, 'user') else 0) else 'normal'
                })
            
            # 计算时间估算
            time_estimates = calculate_queue_time_estimates(cursor, stats[0] or 0, current_task)
        
        # 构建响应数据
        response_data = {
            "queue_stats": {
                "pending": stats[0] or 0,
                "processing": stats[1] or 0,
                "completed": stats[2] or 0,
                "failed": stats[3] or 0
            },
            "current_task": current_task,
            "pending_tasks": pending_tasks,
            "time_estimates": time_estimates
        }
        
        # 更新缓存
        queue_status_cache['data'] = response_data
        queue_status_cache['last_update'] = current_time
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"获取队列状态失败: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


def process_upload_task(task_id):
    """处理上传任务的后台函数 - 优化版本，支持连贯进度更新"""
    global current_processing_task
    
    # 获取任务处理锁
    with task_processing_lock:
        current_processing_task = task_id
        logger.info(f"开始处理上传任务: {task_id}")
        
        try:
            # 更新任务状态为处理中
            update_task_status(task_id, 'processing', 0, started_at=datetime.now())
            
            # 获取任务详情
            task_info = get_task_info(task_id)
            if not task_info:
                logger.error(f"任务 {task_id} 不存在")
                return
            
            # 初始化文档处理器
            config = {
                'chunking_method': task_info['chunking_method'],
                'chunk_size': task_info['chunk_size'],
                'similarity_threshold': task_info['similarity_threshold'],
                'overlap_size': task_info['overlap_size'],
                'custom_delimiter': task_info['custom_delimiter'],
                'window_size': task_info['window_size'],
                'step_size': task_info['step_size'],
                'min_chunk_size': task_info['min_chunk_size'],
                'max_chunk_size': task_info['max_chunk_size']
            }
            
            # 更新进度：初始化处理器 (5%)
            update_task_status(task_id, 'processing', 5, 
                             status_message="正在初始化文档处理器...")
            
            # 自动选择合适的文档处理器，优先使用LlamaParse等高级处理器
            document_processor = get_document_processor(task_info['file_path'], None, config)
            
            # 更新进度：开始处理文档 (10%)
            update_task_status(task_id, 'processing', 10, 
                             status_message="正在提取文档内容...")
            
            # 处理文档内容
            doc_text = document_processor.extract_text(task_info['file_path'])
            if not doc_text:
                raise Exception("提取文档内容失败")
            
            # 更新进度：文档处理完成 (25%)
            update_task_status(task_id, 'processing', 25, 
                             status_message="文档内容提取完成，开始分块...")
            
            # 文本分块
            chunks = document_processor.split_text(doc_text)
            chunk_count = len(chunks)
            
            if chunk_count == 0:
                raise Exception("文档分块失败，未生成有效分块")
            
            # 更新进度：分块完成 (40%)
            update_task_status(task_id, 'processing', 40, 
                             status_message=f"文档分块完成，共生成 {chunk_count} 个分块")
            
            # 获取知识库信息
            kb_info = get_knowledge_database_info(task_info['database_id'])
            if not kb_info:
                raise Exception("知识库不存在")
            
            # 获取知识库对应的embedding模型配置
            from system_mgt.utils.llms_manager import llms_manager
            
            # 从数据库查找知识库对应的embedding模型
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT em.id, em.name, em.model_type, em.api_type, em.api_key, em.api_url, 
                           em.model_name, em.local_path, em.vector_dimension
                    FROM embedding_model em
                    INNER JOIN knowledge_database kb ON kb.embedding_model_id = em.id
                    WHERE kb.id = %s
                """, [task_info['database_id']])
                
                model_config = cursor.fetchone()
                if not model_config:
                    raise Exception(f"知识库 {task_info['database_id']} 未配置embedding模型")
                
                # 构建模型配置字典
                model_config_dict = {
                    'id': model_config[0],
                    'name': model_config[1],
                    'model_type': model_config[2],
                    'api_type': model_config[3],
                    'api_key': model_config[4],
                    'api_url': model_config[5],
                    'model_name': model_config[6],
                    'local_path': model_config[7],
                    'vector_dimension': model_config[8]
                }
            
            # 按需加载知识库对应的embedding模型
            success = llms_manager.ensure_knowledge_base_model_loaded(task_info['database_id'], model_config_dict)
            if not success:
                raise Exception(f"加载知识库 {task_info['database_id']} 的embedding模型失败")
            
            # 激活该知识库的embedding模型
            success = llms_manager.set_active_knowledge_base(task_info['database_id'])
            if not success:
                raise Exception(f"激活知识库 {task_info['database_id']} 的embedding模型失败")
            
            # 获取激活的embedding模型
            embedding_model = llms_manager.get_current_embed_model()
            if embedding_model is None:
                raise Exception("embedding模型激活失败")
            
            # 更新进度：开始生成向量 (50%)
            update_task_status(task_id, 'processing', 50, 
                             status_message="正在加载嵌入模型...")
            
            # 初始化向量存储
            # 从模型配置获取向量维度
            actual_dimension = model_config_dict['vector_dimension']
            vector_store = VectorStore(vector_dimension=actual_dimension, index_type=kb_info['index_type'])
            
            # 更新进度：向量存储初始化完成 (55%)
            update_task_status(task_id, 'processing', 55, 
                             status_message="向量存储初始化完成，开始创建文档记录...")
            
            # 开始数据库事务
            with transaction.atomic():
                # 1. 添加文档记录
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO knowledge_document 
                        (database_id, filename, file_path, file_type, file_size, 
                         chunking_method, chunk_size, chunk_count, user_id, username, create_time, update_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """, [
                        task_info['database_id'], task_info['filename'], task_info['file_path'],
                        os.path.splitext(task_info['filename'])[1], task_info['file_size'],
                        task_info['chunking_method'], task_info['chunk_size'], chunk_count,
                        task_info['user_id'], task_info['username']
                    ])
                    
                    cursor.execute("SELECT LAST_INSERT_ID()")
                    document_id = cursor.fetchone()[0]
                
                # 更新进度：文档记录创建完成 (60%)
                update_task_status(task_id, 'processing', 60, 
                                 status_message="文档记录创建完成，开始文本过滤...")
                
                # 2. 文本过滤处理（停用词和敏感词）
                logger.info(f"开始对文档分块进行文本过滤，共 {len(chunks)} 个分块")
                text_filter = TextFilter()
                
                # 更新进度：开始文本过滤 (62%)
                update_task_status(task_id, 'processing', 62, 
                                 status_message="正在加载停用词和敏感词...")
                
                # 加载启用的停用词与敏感词（与词库管理一致的逻辑）
                try:
                    active_stop_words = list(StopWord.objects.filter(is_active=True).values('word', 'language', 'category', 'description'))
                    text_filter.load_stop_words(active_stop_words)
                except Exception as e:
                    logger.warning(f"加载停用词失败，继续处理: {e}")
                
                try:
                    active_sensitive_words = list(SensitiveWord.objects.filter(is_active=True).values('word', 'level', 'replacement', 'category', 'description'))
                    text_filter.load_sensitive_words(active_sensitive_words)
                except Exception as e:
                    logger.warning(f"加载敏感词失败，继续处理: {e}")
                
                # 更新进度：开始处理分块 (65%)
                update_task_status(task_id, 'processing', 65, 
                                 status_message=f"正在对 {len(chunks)} 个分块进行文本过滤...")
                
                # 过滤后的分块
                filtered_chunks = []
                for i, chunk_text in enumerate(chunks):
                    try:
                        # 使用LlamaParse进行文本过滤
                        filter_result = text_filter.filter_text_with_llamaparse(chunk_text, 'both')
                        filtered_text = filter_result['filtered_text']
                        
                        # 记录过滤统计
                        stop_words_count = filter_result['statistics']['stop_words_count']
                        sensitive_words_count = filter_result['statistics']['sensitive_words_count']
                        
                        if stop_words_count > 0 or sensitive_words_count > 0:
                            logger.info(f"分块 {i+1} 过滤完成: 移除停用词 {stop_words_count} 个, 替换敏感词 {sensitive_words_count} 个")
                        
                        filtered_chunks.append(filtered_text)
                        
                        # 实时更新进度：每处理10个分块更新一次
                        if (i + 1) % 10 == 0 or i == len(chunks) - 1:
                            progress = 65 + int((i + 1) / len(chunks) * 10)
                            update_task_status(task_id, 'processing', progress, 
                                             status_message=f"文本过滤进度: {i + 1}/{len(chunks)} 分块")
                        
                    except Exception as e:
                        logger.warning(f"分块 {i+1} 文本过滤失败，使用原始内容: {e}")
                        filtered_chunks.append(chunk_text)
                
                # 更新进度：文本过滤完成 (75%)
                update_task_status(task_id, 'processing', 75, 
                                 status_message="文本过滤完成，正在创建分块记录...")
                
                # 3. 添加文档分块记录（使用过滤后的内容）
                chunk_ids = []
                for i, chunk_text in enumerate(filtered_chunks):
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO knowledge_document_chunk 
                            (document_id, database_id, chunk_index, content, create_time, update_time)
                            VALUES (%s, %s, %s, %s, NOW(), NOW())
                        """, [document_id, task_info['database_id'], i + 1, chunk_text])
                        
                        cursor.execute("SELECT LAST_INSERT_ID()")
                        chunk_id = cursor.fetchone()[0]
                        chunk_ids.append(chunk_id)
                    
                    # 实时更新进度：每处理10个分块更新一次
                    if (i + 1) % 10 == 0 or i == len(filtered_chunks) - 1:
                        progress = 75 + int((i + 1) / len(filtered_chunks) * 10)
                        update_task_status(task_id, 'processing', progress, 
                                         status_message=f"分块记录创建进度: {i + 1}/{len(filtered_chunks)} 分块")
                
                # 更新进度：分块记录创建完成 (85%)
                update_task_status(task_id, 'processing', 85, 
                                 status_message="分块记录创建完成，开始生成向量...")
                
                # 3. 生成向量并存储
                update_task_status(task_id, 'processing', 87, 
                                 status_message="正在创建向量索引...")
                vector_store.create_index(task_info['database_id'])
                
                # 更新进度：开始生成向量 (88%)
                update_task_status(task_id, 'processing', 88, 
                                 status_message=f"正在为 {len(filtered_chunks)} 个分块生成向量...")
                
                # 使用LlamaIndex的embedding模型生成向量（基于过滤后的内容）
                vectors = []
                for i, chunk_text in enumerate(filtered_chunks):
                    try:
                        vector = embedding_model.get_text_embedding(chunk_text)
                        vectors.append(vector)
                        
                        # 实时更新进度：每处理5个分块更新一次
                        if (i + 1) % 5 == 0 or i == len(filtered_chunks) - 1:
                            progress = 88 + int((i + 1) / len(filtered_chunks) * 8)
                            update_task_status(task_id, 'processing', progress, 
                                             status_message=f"向量生成进度: {i + 1}/{len(filtered_chunks)} 分块")
                        
                    except Exception as e:
                        logger.error(f"生成向量失败: {str(e)}")
                        raise Exception(f"生成向量失败: {str(e)}")
                
                # 更新进度：向量生成完成 (96%)
                update_task_status(task_id, 'processing', 96, 
                                 status_message="向量生成完成，正在存储到向量数据库...")
                
                vector_ids = vector_store.add_vectors(task_info['database_id'], chunk_ids, vectors)
                
                # 更新进度：向量存储完成 (98%)
                update_task_status(task_id, 'processing', 98, 
                                 status_message="向量存储完成，正在更新数据库记录...")
                
                # 4. 更新分块的向量ID
                if vector_ids:
                    for i, chunk_id in enumerate(chunk_ids):
                        vector_id = i if i < len(vector_ids) else None
                        if vector_id is not None:
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    UPDATE knowledge_document_chunk 
                                    SET vector_id = %s
                                    WHERE id = %s
                                """, [str(vector_id), chunk_id])
                
                # 5. 更新知识库的文档数量
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE knowledge_database 
                        SET doc_count = doc_count + 1
                        WHERE id = %s
                    """, [task_info['database_id']])
                
                # 更新任务状态为完成
                update_task_status(task_id, 'completed', 100, 
                                 completed_at=datetime.now(), 
                                 chunk_count=chunk_count,
                                 document_id=document_id)
                
                logger.info(f"任务 {task_id} 处理完成，生成文档ID: {document_id}, 分块数: {chunk_count}")
                
        except Exception as e:
            logger.error(f"处理任务 {task_id} 失败: {str(e)}", exc_info=True)
            update_task_status(task_id, 'failed', error_message=str(e))
        
        finally:
            current_processing_task = None


def update_task_status(task_id, status, progress=None, error_message=None, 
                      started_at=None, completed_at=None, chunk_count=None, document_id=None,
                      status_message=None):
    """更新任务状态 - 支持状态消息"""
    try:
        with connection.cursor() as cursor:
            # 构建更新SQL
            update_fields = ["status = %s", "updated_at = NOW()"]
            params = [status]
            
            if progress is not None:
                update_fields.append("progress = %s")
                params.append(progress)
            
            if error_message is not None:
                update_fields.append("error_message = %s")
                params.append(error_message)
            
            if status_message is not None:
                update_fields.append("status_message = %s")
                params.append(status_message)
            
            if started_at is not None:
                update_fields.append("started_at = %s")
                params.append(started_at)
            
            if completed_at is not None:
                update_fields.append("completed_at = %s")
                params.append(completed_at)
            
            if chunk_count is not None:
                update_fields.append("chunk_count = %s")
                params.append(chunk_count)
            
            if document_id is not None:
                update_fields.append("document_id = %s")
                params.append(document_id)
            
            params.append(task_id)
            
            sql = f"UPDATE document_upload_task SET {', '.join(update_fields)} WHERE task_id = %s"
            cursor.execute(sql, params)
            
            # 清除队列状态缓存
            queue_status_cache['data'] = None
            queue_status_cache['last_update'] = 0
            
            # 记录进度更新日志
            if progress is not None and status_message:
                logger.info(f"任务 {task_id} 进度更新: {progress}% - {status_message}")
            
    except Exception as e:
        logger.error(f"更新任务状态失败: {str(e)}", exc_info=True)


def get_task_info(task_id):
    """获取任务信息"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT task_id, user_id, username, database_id, filename, file_path, file_size,
                       chunking_method, chunk_size, similarity_threshold, overlap_size,
                       custom_delimiter, window_size, step_size, min_chunk_size, max_chunk_size,
                       status, progress, error_message, chunk_count, document_id, created_at, updated_at
                FROM document_upload_task
                WHERE task_id = %s
            """, [task_id])
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
    except Exception as e:
        logger.error(f"获取任务信息失败: {str(e)}", exc_info=True)
        return None


def get_knowledge_database_info(database_id):
    """获取知识库信息"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, vector_dimension, index_type
                FROM knowledge_database
                WHERE id = %s
            """, [database_id])
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'vector_dimension': row[2],
                    'index_type': row[3]
                }
            return None
            
    except Exception as e:
        logger.error(f"获取知识库信息失败: {str(e)}", exc_info=True)
        return None


@require_http_methods(["GET"])
@jwt_required()
def get_task_detail(request, task_id):
    """获取任务详细信息"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        # 获取任务信息
        task_info = get_task_info(task_id)
        if not task_info:
            return create_error_response("任务不存在", 404)
        
        # 检查权限：只能查看自己的任务
        if task_info.get('user_id') != user_id and user_info.get('role_id') != 1:
            return create_error_response("无权限查看此任务", 403)
        
        # 获取任务状态信息
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT status, progress, error_message, started_at, completed_at, 
                       chunk_count, document_id, created_at, updated_at
                FROM document_upload_task
                WHERE task_id = %s
            """, [task_id])
            
            status_info = cursor.fetchone()
            if status_info:
                columns = [desc[0] for desc in cursor.description]
                status_data = dict(zip(columns, status_info))
                
                # 合并任务信息和状态信息
                task_detail = {**task_info, **status_data}
                
                # 如果有文档ID，获取文档信息
                if task_detail.get('document_id'):
                    cursor.execute("""
                        SELECT title, file_type, file_size, chunk_count, create_time
                        FROM knowledge_document
                        WHERE id = %s
                    """, [task_detail.get('document_id')])
                    
                    doc_info = cursor.fetchone()
                    if doc_info:
                        doc_columns = [desc[0] for desc in cursor.description]
                        task_detail['document_info'] = dict(zip(doc_columns, doc_info))
                
                return create_success_response("获取成功", task_detail)
        
        return create_error_response("获取任务详情失败", 500)
        
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}", exc_info=True)
        return create_error_response("获取任务详情失败", 500)


@require_http_methods(["DELETE"])
@csrf_exempt
@jwt_required()
def delete_upload_task(request, task_id):
    """删除上传任务"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        # 获取任务信息
        task_info = get_task_info(task_id)
        if not task_info:
            return create_error_response("任务不存在", 404)
        
        # 检查权限：只能删除自己的任务
        if task_info.get('user_id') != user_id and user_info.get('role_id') != 1:
            return create_error_response("无权限删除此任务", 403)
        
        # 检查任务状态：只能删除等待中或失败的任务
        if task_info.get('status') == 'processing':
            return create_error_response("正在处理中的任务无法删除", 400)
        
        # 删除任务
        with connection.cursor() as cursor:
            # 删除任务记录
            cursor.execute("""
                DELETE FROM document_upload_task 
                WHERE task_id = %s
            """, [task_id])
            
            # 只删除上传的物理文件，保留已处理的文档和分块数据
            if task_info.get('file_path') and os.path.exists(task_info.get('file_path')):
                try:
                    os.remove(task_info.get('file_path'))
                    logger.info(f"已删除上传文件: {task_info.get('file_path')}")
                except Exception as e:
                    logger.warning(f"删除上传文件失败: {str(e)}")
            
            logger.info(f"任务 {task_id} 删除完成，已保留文档内容")
        
        # 清除队列状态缓存
        queue_status_cache['data'] = None
        queue_status_cache['last_update'] = 0
        
        logger.info(f"用户 {user_id} 删除了任务 {task_id}")
        return create_success_response("任务删除成功")
        
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}", exc_info=True)
        return create_error_response("删除任务失败", 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def cancel_upload_task(request, task_id):
    """取消正在处理的上传任务"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        # 获取任务信息
        task_info = get_task_info(task_id)
        if not task_info:
            return create_error_response("任务不存在", 404)
        
        # 检查权限：只能取消自己的任务
        if task_info.get('user_id') != user_id and user_info.get('role_id') != 1:
            return create_error_response("无权限取消此任务", 403)
        
        # 检查任务状态：只能取消正在处理中的任务
        if task_info.get('status') != 'processing':
            return create_error_response("只能取消正在处理中的任务", 400)
        
        # 更新任务状态为已取消
        update_task_status(
            task_id, 
            'cancelled', 
            error_message="任务被用户取消",
            completed_at=datetime.now()
        )
        
        # 清除队列状态缓存
        queue_status_cache['data'] = None
        queue_status_cache['last_update'] = 0
        
        logger.info(f"用户 {user_id} 取消了任务 {task_id}")
        return create_success_response("任务取消成功")
        
    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}", exc_info=True)
        return create_error_response("取消任务失败", 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def clear_completed_tasks(request):
    """清空已完成的任务"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        with connection.cursor() as cursor:
            # 获取用户的任务ID列表
            if user_info.get('role_id') == 1:  # 管理员可以清空所有
                cursor.execute("""
                    SELECT task_id, file_path, document_id 
                    FROM document_upload_task 
                    WHERE status = 'completed'
                """)
            else:  # 普通用户只能清空自己的
                cursor.execute("""
                    SELECT task_id, file_path, document_id 
                    FROM document_upload_task 
                    WHERE status = 'completed' AND user_id = %s
                """, [user_id])
            
            tasks_to_delete = cursor.fetchall()
            
            if not tasks_to_delete:
                return create_success_response("没有已完成的任务需要清空")
            
            deleted_count = 0
            for task in tasks_to_delete:
                task_id, file_path, document_id = task
                
                try:
                    # 删除任务记录
                    cursor.execute("""
                        DELETE FROM document_upload_task 
                        WHERE task_id = %s
                    """, [task_id])
                    
                    # 只删除上传的物理文件，保留已处理的文档和分块数据
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"已删除上传文件: {file_path}")
                        except Exception as e:
                            logger.warning(f"删除上传文件失败: {str(e)}")
                    
                    deleted_count += 1
                    
                except Exception as e:
                    logger.error(f"删除任务 {task_id} 失败: {str(e)}")
                    continue
            
            # 清除队列状态缓存
            queue_status_cache['data'] = None
            queue_status_cache['last_update'] = 0
            
            logger.info(f"用户 {user_id} 清空了 {deleted_count} 个已完成的任务")
            return create_success_response(f"成功清空 {deleted_count} 个已完成的任务")
            
    except Exception as e:
        logger.error(f"清空已完成任务失败: {str(e)}", exc_info=True)
        return create_error_response("清空任务失败", 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def clear_failed_tasks(request):
    """清空失败的任务"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        with connection.cursor() as cursor:
            # 获取用户的任务ID列表
            if user_info.get('role_id') == 1:  # 管理员可以清空所有
                cursor.execute("""
                    SELECT task_id, file_path 
                    FROM document_upload_task 
                    WHERE status = 'failed'
                """)
            else:  # 普通用户只能清空自己的
                cursor.execute("""
                    SELECT task_id, file_path 
                    FROM document_upload_task 
                    WHERE status = 'failed' AND user_id = %s
                """, [user_id])
            
            tasks_to_delete = cursor.fetchall()
            
            if not tasks_to_delete:
                return create_success_response("没有失败的任务需要清空")
            
            deleted_count = 0
            for task in tasks_to_delete:
                task_id, file_path = task
                
                try:
                    # 删除任务记录
                    cursor.execute("""
                        DELETE FROM document_upload_task 
                        WHERE task_id = %s
                    """, [task_id])
                    
                    # 删除上传的物理文件
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"已删除上传文件: {file_path}")
                        except Exception as e:
                            logger.warning(f"删除上传文件失败: {str(e)}")
                    
                    deleted_count += 1
                    
                except Exception as e:
                    logger.error(f"删除任务 {task_id} 失败: {str(e)}")
                    continue
            
            # 清除队列状态缓存
            queue_status_cache['data'] = None
            queue_status_cache['last_update'] = 0
            
            logger.info(f"用户 {user_id} 清空了 {deleted_count} 个失败的任务")
            return create_success_response(f"成功清空 {deleted_count} 个失败的任务")
            
    except Exception as e:
        logger.error(f"清空失败任务失败: {str(e)}", exc_info=True)
        return create_error_response("清空任务失败", 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def clear_all_tasks(request):
    """清空所有任务"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        with connection.cursor() as cursor:
            # 获取用户的任务ID列表
            if user_info.get('role_id') == 1:  # 管理员可以清空所有
                cursor.execute("""
                    SELECT task_id, file_path, document_id, status
                    FROM document_upload_task
                """)
            else:  # 普通用户只能清空自己的
                cursor.execute("""
                    SELECT task_id, file_path, document_id, status
                    FROM document_upload_task 
                    WHERE user_id = %s
                """, [user_id])
            
            tasks_to_delete = cursor.fetchall()
            
            if not tasks_to_delete:
                return create_success_response("没有任务需要清空")
            
            deleted_count = 0
            for task in tasks_to_delete:
                task_id, file_path, document_id, status = task
                
                try:
                    # 删除任务记录
                    cursor.execute("""
                        DELETE FROM document_upload_task 
                        WHERE task_id = %s
                    """, [task_id])
                    
                    # 只删除上传的物理文件，保留已处理的文档和分块数据
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"已删除上传文件: {file_path}")
                        except Exception as e:
                            logger.warning(f"删除上传文件失败: {str(e)}")
                    
                    deleted_count += 1
                    
                except Exception as e:
                    logger.error(f"删除任务 {task_id} 失败: {str(e)}")
                    continue
            
            # 清除队列状态缓存
            queue_status_cache['data'] = None
            queue_status_cache['last_update'] = 0
            
            logger.info(f"用户 {user_id} 清空了 {deleted_count} 个任务")
            return create_success_response(f"成功清空 {deleted_count} 个任务")
            
    except Exception as e:
        logger.error(f"清空所有任务失败: {str(e)}", exc_info=True)
        return create_error_response("清空任务失败", 500)
