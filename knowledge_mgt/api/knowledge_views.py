"""
知识库管理API视图
处理知识库的创建、查询、更新、删除等操作
"""

import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
import json

from zhiqing_server.utils.response_code import ResponseCode
from zhiqing_server.utils.auth_utils import jwt_required, get_user_from_request

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required()
def knowledge_database_list(request):
    """获取知识库列表API"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # 构建查询条件
        where_clause = "1=1"
        params = []
        
        # 普通用户只能看到自己的知识库
        if role_id != 1:  # 非管理员
            where_clause += " AND user_id = %s"
            params.append(user_id)
        
        # 查询总数
        with connection.cursor() as cursor:
            count_sql = f"SELECT COUNT(*) FROM knowledge_database WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()[0]
            
            # 查询知识库列表（实时计算文档数量和嵌入模型信息）
            offset = (page - 1) * page_size
            list_sql = f"""
                SELECT k.id, k.name, k.description, k.vector_dimension, k.index_type,
                       k.user_id, k.username, k.create_time, k.update_time, k.embedding_model_id
                FROM knowledge_database k
                WHERE {where_clause}
                ORDER BY k.create_time DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(list_sql, params + [page_size, offset])
            
            knowledge_bases = []
            for row in cursor.fetchall():
                # 实时计算该知识库的文档数量
                cursor.execute("""
                    SELECT COUNT(*) FROM knowledge_document 
                    WHERE database_id = %s
                """, [row[0]])
                doc_count = cursor.fetchone()[0]
                
                # 获取嵌入模型信息
                embedding_model_info = None
                if row[9]:  # embedding_model_id
                    cursor.execute("""
                        SELECT name, model_type, api_type FROM embedding_model 
                        WHERE id = %s AND is_active = 1
                    """, [row[9]])
                    model_row = cursor.fetchone()
                    if model_row:
                        embedding_model_info = {
                            'id': row[9],
                            'name': model_row[0],
                            'model_type': model_row[1],
                            'api_type': model_row[2]
                        }
                
                knowledge_bases.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'vector_dimension': row[3],
                    'index_type': row[4],
                    'doc_count': doc_count,
                    'user_id': row[5],
                    'username': row[6],
                    'create_time': row[7].strftime("%Y-%m-%d %H:%M:%S") if row[7] else None,
                    'update_time': row[8].strftime("%Y-%m-%d %H:%M:%S") if row[8] else None,
                    'embedding_model_id': row[9],
                    'embedding_model_name': embedding_model_info['name'] if embedding_model_info else None,
                    'embedding_model_type': embedding_model_info['api_type'] if embedding_model_info else None
                })
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(
                data={
                    'list': knowledge_bases,
                    'total': total_count,
                    'page': page,
                    'page_size': page_size
                }
            )
        )
        
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取知识库列表失败: {str(e)}"),
            status=500
        )


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required()
def check_knowledge_database_name(request):
    """检查知识库名称是否重复API"""
    try:
        name = request.GET.get('name', '').strip()
        if not name:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="知识库名称不能为空"),
                status=400
            )
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        with connection.cursor() as cursor:
            # 检查名称是否重复（同一用户下不能重复）
            cursor.execute("""
                SELECT COUNT(*) FROM knowledge_database 
                WHERE name = %s AND user_id = %s
            """, [name, user_id])
            
            count = cursor.fetchone()[0]
            is_available = count == 0
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(
                data={
                    'name': name,
                    'is_available': is_available
                }
            )
        )
        
    except Exception as e:
        logger.error(f"检查知识库名称失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"检查知识库名称失败: {str(e)}"),
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required()
def create_knowledge_database(request):
    """创建知识库API"""
    try:
        # 解析请求数据
        data = json.loads(request.body)
        logger.info(f"创建知识库请求数据: {data}")
        
        # 验证必填字段
        required_fields = ['name', 'description', 'vector_dimension', 'index_type']
        for field in required_fields:
            if not data.get(field):
                logger.error(f"缺少必填字段: {field}")
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"缺少必填字段: {field}"),
                    status=400
                )
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        vector_dimension = int(data.get('vector_dimension', 1536))
        index_type = data.get('index_type', 'faiss')
        embedding_model_id = data.get('embedding_model_id')
        
        # 如果embedding_model_id为null或空字符串，设置为None
        if embedding_model_id == '' or embedding_model_id == 'null':
            embedding_model_id = None
        
        logger.info(f"处理后的数据: name={name}, description={description}, vector_dimension={vector_dimension}, index_type={index_type}, embedding_model_id={embedding_model_id}")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        user_name = user_info.get('user_name', '未知用户')
        
        logger.info(f"用户信息: user_id={user_id}, user_name={user_name}")
        
        with connection.cursor() as cursor:
            # 检查名称是否重复
            cursor.execute("""
                SELECT COUNT(*) FROM knowledge_database 
                WHERE name = %s AND user_id = %s
            """, [name, user_id])
            
            if cursor.fetchone()[0] > 0:
                logger.warning(f"知识库名称已存在: {name}")
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库名称已存在"),
                    status=400
                )
            
            # 创建知识库
            insert_sql = """
                INSERT INTO knowledge_database 
                (name, description, vector_dimension, index_type, doc_count, user_id, username, embedding_model_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            insert_params = (name, description, vector_dimension, index_type, 0, user_id, user_name, embedding_model_id)
            logger.info(f"执行SQL: {insert_sql}")
            logger.info(f"SQL参数: {insert_params}")
            
            cursor.execute(insert_sql, insert_params)
            
            knowledge_id = cursor.lastrowid
            connection.commit()
            
            logger.info(f"知识库创建成功，ID: {knowledge_id}")
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(
                message="知识库创建成功",
                data={'id': knowledge_id}
            )
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="请求数据格式错误"),
            status=400
        )
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"创建知识库失败: {str(e)}"),
            status=500
        )


@csrf_exempt
@require_http_methods(["PUT"])
@jwt_required()
def update_knowledge_database(request, knowledge_id):
    """更新知识库API"""
    try:
        # 解析请求数据
        data = json.loads(request.body)
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        with connection.cursor() as cursor:
            # 检查知识库是否存在和权限
            cursor.execute("""
                SELECT user_id FROM knowledge_database WHERE id = %s
            """, [knowledge_id])
            
            kb_row = cursor.fetchone()
            if not kb_row:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库不存在"),
                    status=404
                )
            
            kb_user_id = kb_row[0]
            
            # 权限检查：只有创建者或管理员可以修改
            if role_id != 1 and kb_user_id != user_id:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="无权限修改此知识库"),
                    status=403
                )
            
            # 构建更新字段
            update_fields = []
            update_params = []
            
            if 'name' in data:
                name = data['name'].strip()
                if name:
                    update_fields.append("name = %s")
                    update_params.append(name)
            
            if 'description' in data:
                description = data['description'].strip()
                update_fields.append("description = %s")
                update_params.append(description)
            
            if 'vector_dimension' in data:
                vector_dimension = int(data['vector_dimension'])
                update_fields.append("vector_dimension = %s")
                update_params.append(vector_dimension)
            
            if 'index_type' in data:
                index_type = data['index_type']
                update_fields.append("index_type = %s")
                update_params.append(index_type)
            
            if 'embedding_model_id' in data:
                embedding_model_id = data['embedding_model_id']
                update_fields.append("embedding_model_id = %s")
                update_params.append(embedding_model_id)
            
            if not update_fields:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="没有需要更新的字段"),
                    status=400
                )
            
            # 执行更新
            update_sql = f"""
                UPDATE knowledge_database 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            cursor.execute(update_sql, update_params + [knowledge_id])
            connection.commit()
            
            logger.info(f"知识库更新成功，ID: {knowledge_id}")
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="知识库更新成功")
        )
        
    except json.JSONDecodeError:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="请求数据格式错误"),
            status=400
        )
    except Exception as e:
        logger.error(f"更新知识库失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"更新知识库失败: {str(e)}"),
            status=500
        )


@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required()
def delete_knowledge_database(request, knowledge_id):
    """删除知识库API"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        with connection.cursor() as cursor:
            # 检查知识库是否存在和权限
            cursor.execute("""
                SELECT user_id FROM knowledge_database WHERE id = %s
            """, [knowledge_id])
            
            kb_row = cursor.fetchone()
            if not kb_row:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库不存在"),
                    status=404
                )
            
            kb_user_id = kb_row[0]
            
            # 权限检查：只有创建者或管理员可以删除
            if role_id != 1 and kb_user_id != user_id:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="无权限删除此知识库"),
                    status=403
                )
            
            # 检查是否有文档关联
            cursor.execute("""
                SELECT COUNT(*) FROM knowledge_document WHERE database_id = %s
            """, [knowledge_id])
            
            doc_count = cursor.fetchone()[0]
            if doc_count > 0:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"知识库中还有 {doc_count} 个文档，无法删除"),
                    status=400
                )
            
            # 删除知识库
            cursor.execute("""
                DELETE FROM knowledge_database WHERE id = %s
            """, [knowledge_id])
            
            connection.commit()
            
            logger.info(f"知识库删除成功，ID: {knowledge_id}")
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="知识库删除成功")
        )
        
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"删除知识库失败: {str(e)}"),
            status=500
        )
