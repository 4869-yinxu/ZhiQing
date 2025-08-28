"""
文档管理API视图
支持多格式文档上传和处理
"""

import os
import logging
import uuid
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db import connection
import json

from zhiqing_server.utils.response_code import ResponseCode
from zhiqing_server.utils.auth_utils import jwt_required, get_user_from_request

from ..utils.document_processor import get_document_processor, get_supported_formats

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required()
def upload_document(request):
    """上传文档API - 支持多格式"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        if not user_info:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="无法获取用户信息"),
                status=401
            )
        
        user_id = user_info.get('user_id')
        
        # 获取知识库ID
        database_id = request.POST.get('database_id')
        if not database_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="请选择知识库"),
                status=400
            )
        
        # 检查是否有文件上传
        if 'file' not in request.FILES:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="请选择要上传的文件"),
                status=400
            )
        
        upload_file = request.FILES['file']
        file_name = upload_file.name
        file_size = upload_file.size
        
        # 获取文件扩展名
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # 检查支持的文件格式
        supported_formats = get_supported_formats()
        if file_extension not in supported_formats:
            logger.warning(f"上传文档失败: 不支持的文件格式 {file_extension}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(
                    message=f"不支持的文件格式 {file_extension}。支持格式: {', '.join(supported_formats)}"
                ),
                status=400
            )
        
        # 检查文件大小（50MB限制）
        max_file_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_file_size:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="文件大小不能超过50MB"),
                status=400
            )
        
        # 保存文件到media目录
        file_path = os.path.join(settings.MEDIA_ROOT, 'documents', file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb+') as destination:
            for chunk in upload_file.chunks():
                destination.write(chunk)
        
        logger.info(f"文件保存成功: {file_path}")
        
        try:
            # 使用新的文档处理器处理文件
            processor = get_document_processor(file_path)
            logger.info(f"使用处理器: {processor.processor_name}")
            
            # 提取文本内容
            text_content = processor.extract_text(file_path)
            if not text_content:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="文档内容提取失败"),
                    status=400
                )
            
            # 提取文档结构
            structure_info = processor.extract_structure(file_path)
            
            # 保存文档信息到数据库
            with connection.cursor() as cursor:
                # 插入文档记录
                insert_doc_sql = """
                INSERT INTO knowledge_document 
                (database_id, filename, file_path, file_type, file_size, chunking_method, chunk_size, 
                 chunk_count, user_id, username, create_time, update_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                
                # 使用默认分块参数
                chunking_method = 'token'
                chunk_size = 1000
                chunk_count = 1  # 默认值，后续会更新
                
                cursor.execute(insert_doc_sql, (
                    int(database_id),  # 确保是整数类型
                    file_name,
                    file_path,
                    file_extension,
                    file_size,
                    chunking_method,
                    chunk_size,
                    chunk_count,
                    user_id,
                    user_info.get('user_name', 'unknown')
                ))
                
                document_id = cursor.lastrowid
                logger.info(f"文档记录保存成功，ID: {document_id}")
                
                # 文本分块处理
                if hasattr(processor, 'split_text'):
                    # 使用处理器的分块功能
                    chunks = processor.split_text(text_content)
                else:
                    # 回退到简单分块
                    chunks = _simple_text_chunking(text_content)
                
                # 保存文本块
                for i, chunk in enumerate(chunks):
                    if chunk.strip():
                        insert_chunk_sql = """
                        INSERT INTO knowledge_document_chunk
                        (document_id, database_id, chunk_index, content, create_time, update_time)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                        """
                        
                        cursor.execute(insert_chunk_sql, (
                            document_id,
                            int(database_id),  # 确保是整数类型
                            i + 1,
                            chunk
                        ))
                
                # 更新chunk_count
                chunk_count = len(chunks)
                cursor.execute("UPDATE knowledge_document SET chunk_count = %s WHERE id = %s", (chunk_count, document_id))
                
                connection.commit()
                logger.info(f"文档处理完成，生成 {chunk_count} 个文本块")
                
                # 开始向量化处理
                try:
                    logger.info(f"开始为文档 {document_id} 生成向量索引")
                    
                    # 获取知识库信息
                    cursor.execute("""
                        SELECT vector_dimension, index_type, embedding_model_id 
                        FROM knowledge_database 
                        WHERE id = %s
                    """, [database_id])
                    kb_info = cursor.fetchone()
                    
                    if kb_info and kb_info[2]:  # 如果有嵌入模型
                        vector_dimension = kb_info[0]
                        index_type = kb_info[1]
                        embedding_model_id = kb_info[2]
                        
                        # 获取嵌入模型配置
                        cursor.execute("""
                            SELECT local_path, model_name, vector_dimension
                            FROM embedding_model 
                            WHERE id = %s AND is_active = 1
                        """, [embedding_model_id])
                        model_info = cursor.fetchone()
                        
                        if model_info and model_info[0]:  # 如果有本地模型路径
                            # 创建嵌入模型实例
                            from ..utils.embeddings import EmbeddingModel
                            embedding_model = EmbeddingModel(
                                model_name=model_info[1] or "all-MiniLM-L6-v2",
                                model_config={'local_path': model_info[0]}
                            )
                            
                            try:
                                # 加载模型
                                embedding_model.load_model()
                                
                                if embedding_model.is_loaded:
                                    # 生成向量
                                    from ..utils.vector_store import VectorStore
                                    vector_store = VectorStore(vector_dimension=vector_dimension, index_type=index_type)
                                    
                                    # 创建或更新向量索引（包含权限验证）
                                    vector_store.create_index(int(database_id), user_id=user_id, role_id=role_id)
                                    
                                    # 为每个分块生成向量
                                    chunk_contents = [chunk for chunk in chunks if chunk.strip()]
                                    vectors = embedding_model.embed_texts(chunk_contents)
                                    
                                    # 获取分块ID
                                    cursor.execute("""
                                        SELECT id FROM knowledge_document_chunk 
                                        WHERE document_id = %s 
                                        ORDER BY chunk_index
                                    """, [document_id])
                                    chunk_rows = cursor.fetchall()
                                    chunk_ids = [row[0] for row in chunk_rows]
                                    
                                    # 添加向量到索引（包含权限验证）
                                    vector_ids = vector_store.add_vectors(int(database_id), chunk_ids, vectors, user_id=user_id, role_id=role_id)
                                    
                                    # 更新分块的向量ID
                                    if vector_ids:
                                        for i, chunk_id in enumerate(chunk_ids):
                                            if i < len(vector_ids):
                                                cursor.execute("""
                                                    UPDATE knowledge_document_chunk 
                                                    SET vector_id = %s
                                                    WHERE id = %s
                                                """, [str(vector_ids[i]), chunk_id])
                                    
                                    connection.commit()
                                    logger.info(f"文档 {document_id} 向量化完成，生成了 {len(vectors)} 个向量")
                                else:
                                    logger.warning(f"嵌入模型 {embedding_model_id} 未加载，跳过向量化")
                            except Exception as model_error:
                                logger.error(f"嵌入模型加载失败: {str(model_error)}")
                        else:
                            logger.info(f"知识库 {database_id} 未配置嵌入模型，跳过向量化")
                        
                except Exception as vector_error:
                    logger.error(f"文档 {document_id} 向量化失败: {str(vector_error)}")
                    # 向量化失败不影响文档上传的成功状态
            
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(data={
                    "message": "文档上传成功",
                    "document_id": document_id,
                    "file_name": file_name,
                    "file_type": file_extension,
                    "file_size": file_size,
                    "chunk_count": len(chunks),
                    "structure_info": structure_info,
                    "vectorized": True  # 标记是否已向量化
                }),
                status=200
            )
            
        except Exception as e:
            logger.error(f"文档处理失败: {str(e)}", exc_info=True)
            # 清理已保存的文件
            try:
                os.remove(file_path)
            except:
                pass
            
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message=f"文档处理失败: {str(e)}"),
                status=500
            )
            
    except Exception as e:
        logger.error(f"上传文档异常: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"上传文档失败: {str(e)}"),
            status=500
        )


def _simple_text_chunking(text: str, chunk_size: int = 1000) -> list:
    """简单的文本分块（回退方案）"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # 尝试在合适的位置断开
        if end < len(text):
            # 寻找句号、换行等自然断点
            for i in range(min(100, end - start)):
                if text[end - i] in ['.', '!', '?', '\n', '。', '！', '？', '；', ';']:
                    end = end - i + 1
                    break
        
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        
        start = end
    
    return chunks


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required()
def create_web_crawl(request):
    """创建网页抓取任务（入队异步处理，首次请求立即返回task_id）"""
    try:
        # 解析请求体
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = request.POST.dict()

        database_id = body.get('database_id')
        url = body.get('url')
        title = body.get('title') or ''
        chunking_method = body.get('chunking_method', 'semantic')
        chunk_size = int(body.get('chunk_size', 500))
        similarity_threshold = float(body.get('similarity_threshold', 0.7))
        min_chunk_size = int(body.get('min_chunk_size', 50))
        max_chunk_size = int(body.get('max_chunk_size', 2000))

        logger.info(f"接收网页抓取请求: database_id={database_id}, url={url}, title={title}")

        if not database_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="请选择知识库"),
                status=400
            )
        if not url:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="请输入有效的网页地址"),
                status=400
            )

        # 校验知识库是否存在
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(1) FROM knowledge_database WHERE id=%s", [int(database_id)])
                exists = cursor.fetchone()[0]
                if not exists:
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message="知识库不存在或已删除"),
                        status=400
                    )
        except Exception as db_check_err:
            logger.error(f"校验知识库失败: {db_check_err}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="校验知识库失败，请稍后重试"),
                status=500
            )

        # 用户信息
        user_info = get_user_from_request(request) or {}
        user_id = user_info.get('user_id')
        username = user_info.get('user_name', 'unknown')

        # 生成任务ID与文件名
        from urllib.parse import urlparse
        parsed = urlparse(url)
        derived_name = title.strip() if title else (parsed.netloc + parsed.path).strip('/') or parsed.netloc
        filename = (derived_name[:200] or 'webpage') + '.html'
        task_id = str(uuid.uuid4())

        # 插入上传队列（file_path 存URL，file_size 先置0）
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO document_upload_task 
                (task_id, user_id, username, database_id, filename, file_path, file_size,
                 chunking_method, chunk_size, similarity_threshold, overlap_size,
                 custom_delimiter, window_size, step_size, min_chunk_size, max_chunk_size,
                 status, progress)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    task_id, user_id, username, int(database_id), filename, url, 0,
                    chunking_method, chunk_size, similarity_threshold, 100,
                    '\n\n', 3, 1, min_chunk_size, max_chunk_size,
                    'pending', 0
                ]
            )

        logger.info(f"创建网页抓取任务: {task_id}, URL: {url}, 文件名: {filename}")

        # 启动异步处理线程（复用现有处理逻辑）
        try:
            from .upload_task_views import process_upload_task
            threading.Thread(target=process_upload_task, args=(task_id,), daemon=True).start()
        except Exception as te:
            logger.error(f"启动网页抓取任务线程失败: {te}")

        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                'message': '网页抓取任务创建成功，已加入队列',
                'task_id': task_id,
                'filename': filename,
                'status': 'pending'
            }),
            status=200
        )

    except Exception as e:
        logger.error(f"网页抓取处理失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"网页抓取处理失败: {str(e)}"),
            status=500,
        )
@require_http_methods(["GET"])
@jwt_required()
def get_supported_formats_api(request):
    """获取支持的文件格式API"""
    try:
        # 获取支持的文件格式
        supported_formats = get_supported_formats()
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                "supported_formats": supported_formats,
                "format_descriptions": {
                    '.txt': '纯文本文件',
                    '.md': 'Markdown文档',
                    '.docx': 'Word文档',
                    '.doc': 'Word文档（旧格式）',
                    '.pdf': 'PDF文档',
                    '.xlsx': 'Excel表格',
                    '.xls': 'Excel表格（旧格式）',
                    '.csv': 'CSV表格'
                }
            }),
            status=200
        )
        
    except Exception as e:
        logger.error(f"获取支持格式失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取支持格式失败: {str(e)}"),
            status=500
        )


@require_http_methods(["GET"])
@jwt_required()
def get_processor_info_api(request):
    """获取处理器信息API"""
    try:
        from ..utils.document_processor import get_processor_info
        processor_info = get_processor_info()
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data=processor_info),
            status=200
        )
        
    except Exception as e:
        logger.error(f"获取处理器信息失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取处理器信息失败: {str(e)}"),
            status=500
        )


@require_http_methods(["GET"])
@jwt_required()
def document_list_api(request):
    """获取文档列表API"""
    try:
        # 获取查询参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        database_id = request.GET.get('database_id', '')
        file_type = request.GET.get('file_type', '')
        keyword = request.GET.get('keyword', '')
        
        # 构建查询条件
        conditions = []
        params = []
        
        # 必须指定知识库ID
        if not database_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="必须指定知识库ID"),
                status=400
            )
        
        conditions.append("database_id = %s")
        params.append(database_id)
        
        if file_type:
            conditions.append("file_type = %s")
            params.append(file_type)
        
        if keyword:
            conditions.append("(filename LIKE %s OR content LIKE %s)")
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        with connection.cursor() as cursor:
            count_sql = f"SELECT COUNT(*) FROM knowledge_document WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()[0]
            
            # 查询文档列表
            offset = (page - 1) * page_size
            list_sql = f"""
            SELECT id, filename, file_type, file_size, create_time, chunk_count, create_time
            FROM knowledge_document 
            WHERE {where_clause}
            ORDER BY create_time DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(list_sql, params + [page_size, offset])
            
            documents = []
            for row in cursor.fetchall():
                documents.append({
                    'id': row[0],
                    'filename': row[1],
                    'title': row[1],  # 保持兼容性，同时返回filename和title
                    'file_type': row[2],
                    'file_size': row[3],
                    'upload_time': row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None,
                    'chunk_count': row[5],
                    'created_at': row[6].strftime("%Y-%m-%d %H:%M:%S") if row[6] else None
                })
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                'list': documents,  # 前端期望的字段名
                'total': total_count,  # 前端期望的字段名
                'page': page,
                'page_size': page_size
            }),
            status=200
        )
        
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取文档列表失败: {str(e)}"),
            status=500
        )


@require_http_methods(["GET"])
@jwt_required()
def document_detail_api(request, doc_id):
    """获取文档详情API"""
    try:
        with connection.cursor() as cursor:
            # 查询文档详情
            cursor.execute("""
                SELECT id, title, file_path, file_type, file_size, content, 
                       structure_info, upload_user_id, upload_time, status, created_at
                FROM knowledge_document 
                WHERE id = %s
            """, [doc_id])
            
            row = cursor.fetchone()
            if not row:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="文档不存在"),
                    status=404
                )
            
            # 查询用户信息
            cursor.execute("""
                SELECT username FROM user WHERE id = %s
            """, [row[7]])
            user_row = cursor.fetchone()
            username = user_row[0] if user_row else "未知用户"
            
            # 查询分块数量
            cursor.execute("""
                SELECT COUNT(*) FROM knowledge_document_chunk WHERE document_id = %s
            """, [doc_id])
            chunk_count = cursor.fetchone()[0]
            
            document_detail = {
                'id': row[0],
                'title': row[1],
                'file_path': row[2],
                'file_type': row[3],
                'file_size': row[4],
                'content': row[5][:500] + "..." if row[5] and len(row[5]) > 500 else row[5],  # 截取前500字符
                'structure_info': json.loads(row[6]) if row[6] else {},
                'upload_user': username,
                'upload_time': row[8].strftime("%Y-%m-%d %H:%M:%S") if row[8] else None,
                'status': row[9],
                'created_at': row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else None,
                'chunk_count': chunk_count
            }
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data=document_detail),
            status=200
        )
        
    except Exception as e:
        logger.error(f"获取文档详情失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取文档详情失败: {str(e)}"),
            status=500
        )


@require_http_methods(["DELETE"])
@jwt_required()
def document_delete_api(request, doc_id):
    """删除文档API"""
    try:
        with connection.cursor() as cursor:
            # 查询文档信息
            cursor.execute("""
                SELECT file_path FROM knowledge_document WHERE id = %s
            """, [doc_id])
            
            row = cursor.fetchone()
            if not row:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="文档不存在"),
                    status=404
                )
            
            file_path = row[0]
            
            # 删除分块记录
            cursor.execute("""
                DELETE FROM knowledge_document_chunk WHERE document_id = %s
            """, [doc_id])
            
            # 删除文档记录
            cursor.execute("""
                DELETE FROM knowledge_document WHERE id = %s
            """, [doc_id])
            
            connection.commit()
            
            # 删除文件
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除文件失败: {e}")
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="文档删除成功"),
            status=200
        )
        
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"删除文档失败: {str(e)}"),
            status=500
        )


@require_http_methods(["GET"])
@jwt_required()
def document_chunks_api(request, doc_id):
    """获取文档分块列表API"""
    try:
        # 获取查询参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        with connection.cursor() as cursor:
            # 查询文档信息
            cursor.execute("""
                SELECT filename, file_type, chunking_method, chunk_size, chunk_count
                FROM knowledge_document WHERE id = %s
            """, [doc_id])
            
            doc_row = cursor.fetchone()
            if not doc_row:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="文档不存在"),
                    status=404
                )
            
            filename, file_type, chunking_method, chunk_size, chunk_count = doc_row
            
            # 查询分块总数
            cursor.execute("""
                SELECT COUNT(*) FROM knowledge_document_chunk WHERE document_id = %s
            """, [doc_id])
            total_chunks = cursor.fetchone()[0]
            
            # 查询分块列表
            offset = (page - 1) * page_size
            cursor.execute("""
                SELECT id, chunk_index, content, create_time
                FROM knowledge_document_chunk 
                WHERE document_id = %s 
                ORDER BY chunk_index 
                LIMIT %s OFFSET %s
            """, [doc_id, page_size, offset])
            
            chunks = []
            for row in cursor.fetchall():
                chunks.append({
                    'id': row[0],
                    'chunk_index': row[1],
                    'content': row[2][:200] + "..." if row[2] and len(row[2]) > 200 else row[2],  # 截取前200字符
                    'full_content': row[2],  # 完整内容
                    'chunk_size': len(row[2]) if row[2] else 0,  # 计算内容长度
                    'created_at': row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else None
                })
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                'document': {
                    'id': doc_id,
                    'filename': filename,
                    'title': filename,  # 保持兼容性
                    'file_type': file_type,
                    'chunking_method': chunking_method,
                    'chunk_size': chunk_size,
                    'chunk_count': chunk_count
                },
                'chunks': chunks,
                'total_chunks': total_chunks,
                'page': page,
                'page_size': page_size
            }),
            status=200
        )
        
    except Exception as e:
        logger.error(f"获取文档分块失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取文档分块失败: {str(e)}"),
            status=500
        )
