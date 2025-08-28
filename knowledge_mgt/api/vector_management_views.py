"""
向量管理API
用于管理不同用户的向量数据库，包括索引信息、清理、重建等操作
"""

import json
import logging
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from zhiqing_server.utils.auth_utils import (
    jwt_required, get_user_from_request, check_resource_permission,
    parse_json_body, validate_required_fields,
    create_error_response, create_success_response
)
from zhiqing_server.utils.db_utils import (
    execute_query_with_params
)
from knowledge_mgt.utils.vector_store import VectorStore

# 获取模块日志记录器
logger = logging.getLogger('knowledge_mgt')


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_vector_index_info(request):
    """获取向量索引信息"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 获取查询参数
        knowledge_db_id = request.GET.get('knowledge_db_id')
        
        if not knowledge_db_id:
            return create_error_response('缺少必填参数: knowledge_db_id')
        
        # 初始化向量存储
        vector_store = VectorStore()
        
        # 获取索引信息（包含权限验证）
        index_info = vector_store.get_index_info(knowledge_db_id, user_id=user_id, role_id=role_id)
        
        if index_info is None:
            return create_error_response('索引不存在或无权限访问', 404)
        
        return create_success_response(index_info)
        
    except Exception as e:
        logger.error(f"获取向量索引信息失败: {str(e)}", exc_info=True)
        return create_error_response(f"获取向量索引信息失败: {str(e)}", 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def list_user_vector_indexes(request):
    """列出用户的所有向量索引"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 构建查询SQL
        if role_id == 1:
            # 管理员可以查看所有知识库
            sql = """
                SELECT kd.id, kd.name, kd.description, kd.vector_dimension, kd.index_type,
                       kd.create_time, kd.update_time, u.username
                FROM knowledge_database kd
                JOIN user u ON kd.user_id = u.id
                WHERE kd.status = 1
                ORDER BY kd.create_time DESC
            """
            params = []
        else:
            # 普通用户只能查看自己的知识库
            sql = """
                SELECT kd.id, kd.name, kd.description, kd.vector_dimension, kd.index_type,
                       kd.create_time, kd.update_time, u.username
                FROM knowledge_database kd
                JOIN user u ON kd.user_id = u.id
                WHERE kd.status = 1 AND kd.user_id = %s
                ORDER BY kd.create_time DESC
            """
            params = [user_id]
        
        # 执行查询
        results = execute_query_with_params(sql, params)
        
        # 获取每个知识库的向量索引信息
        vector_store = VectorStore()
        enhanced_results = []
        
        for kb in results:
            kb_info = {
                'id': kb['id'],
                'name': kb['name'],
                'description': kb['description'],
                'vector_dimension': kb['vector_dimension'],
                'index_type': kb['index_type'],
                'create_time': kb['create_time'],
                'update_time': kb['update_time'],
                'username': kb['username']
            }
            
            # 获取向量索引信息
            index_info = vector_store.get_index_info(kb['id'], user_id=user_id, role_id=role_id)
            if index_info:
                kb_info['vector_index'] = index_info
            else:
                kb_info['vector_index'] = None
            
            enhanced_results.append(kb_info)
        
        return create_success_response({
            'knowledge_bases': enhanced_results,
            'total': len(enhanced_results)
        })
        
    except Exception as e:
        logger.error(f"列出用户向量索引失败: {str(e)}", exc_info=True)
        return create_error_response(f"列出用户向量索引失败: {str(e)}", 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def rebuild_vector_index(request):
    """重建向量索引"""
    try:
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['knowledge_db_id']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        knowledge_db_id = request_data.get('knowledge_db_id')
        
        # 获取知识库信息
        kb_sql = """
            SELECT id, name, vector_dimension, index_type
            FROM knowledge_database 
            WHERE id = %s AND status = 1
        """
        kb_params = [knowledge_db_id]
        
        # 普通用户只能访问自己的知识库
        if role_id != 1:
            kb_sql += " AND user_id = %s"
            kb_params.append(user_id)
        
        kb_result = execute_query_with_params(kb_sql, kb_params)
        if not kb_result:
            return create_error_response('知识库不存在或无权限访问', 404)
        
        kb_info = kb_result[0]
        
        # 获取所有文档分块
        chunks_sql = """
            SELECT dc.id, dc.content
            FROM knowledge_document_chunk dc
            JOIN knowledge_document d ON dc.document_id = d.id
            WHERE d.database_id = %s
            ORDER BY dc.chunk_index
        """
        chunks_params = [knowledge_db_id]
        
        # 普通用户只能访问自己的文档
        if role_id != 1:
            chunks_sql += " AND d.user_id = %s"
            chunks_params.append(user_id)
        
        chunks_result = execute_query_with_params(chunks_sql, chunks_params)
        
        if not chunks_result:
            return create_error_response('知识库中没有文档分块', 400)
        
        # 获取嵌入模型
        from knowledge_mgt.utils.embeddings import local_embedding_manager
        embedding_model = local_embedding_manager.get_current_model()
        
        if embedding_model is None:
            return create_error_response('没有加载的嵌入模型，请先在系统管理中加载嵌入模型', 500)
        
        # 生成向量
        chunk_contents = [chunk['content'] for chunk in chunks_result]
        vectors = embedding_model.embed_texts(chunk_contents)
        
        # 重建索引
        vector_store = VectorStore(
            vector_dimension=embedding_model.get_dimension(),
            index_type=kb_info['index_type']
        )
        
        success = vector_store.rebuild_index(
            knowledge_db_id, 
            vectors, 
            user_id=user_id, 
            role_id=role_id
        )
        
        if success:
            return create_success_response({
                'message': '向量索引重建成功',
                'knowledge_db_id': knowledge_db_id,
                'total_vectors': len(vectors)
            })
        else:
            return create_error_response('向量索引重建失败', 500)
        
    except Exception as e:
        logger.error(f"重建向量索引失败: {str(e)}", exc_info=True)
        return create_error_response(f"重建向量索引失败: {str(e)}", 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def cleanup_vector_index(request):
    """清理向量索引"""
    try:
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['knowledge_db_id']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        knowledge_db_id = request_data.get('knowledge_db_id')
        
        # 初始化向量存储
        vector_store = VectorStore()
        
        # 清理索引（包含权限验证）
        success = vector_store.cleanup_index(knowledge_db_id, user_id=user_id, role_id=role_id)
        
        if success:
            return create_success_response({
                'message': '向量索引清理成功',
                'knowledge_db_id': knowledge_db_id
            })
        else:
            return create_error_response('向量索引清理失败', 500)
        
    except Exception as e:
        logger.error(f"清理向量索引失败: {str(e)}", exc_info=True)
        return create_error_response(f"清理向量索引失败: {str(e)}", 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def delete_vectors(request):
    """删除指定的向量"""
    try:
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['knowledge_db_id', 'vector_ids']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        knowledge_db_id = request_data.get('knowledge_db_id')
        vector_ids = request_data.get('vector_ids')
        
        if not isinstance(vector_ids, list) or not vector_ids:
            return create_error_response('vector_ids必须是非空列表')
        
        # 初始化向量存储
        vector_store = VectorStore()
        
        # 删除向量（包含权限验证）
        success = vector_store.delete_vectors(knowledge_db_id, vector_ids, user_id=user_id, role_id=role_id)
        
        if success:
            return create_success_response({
                'message': '向量删除成功',
                'knowledge_db_id': knowledge_db_id,
                'deleted_count': len(vector_ids)
            })
        else:
            return create_error_response('向量删除失败', 500)
        
    except Exception as e:
        logger.error(f"删除向量失败: {str(e)}", exc_info=True)
        return create_error_response(f"删除向量失败: {str(e)}", 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_vector_statistics(request):
    """获取向量统计信息"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 构建查询SQL
        if role_id == 1:
            # 管理员可以查看所有统计信息
            sql = """
                SELECT 
                    COUNT(*) as total_knowledge_bases,
                    SUM(CASE WHEN kd.status = 1 THEN 1 ELSE 0 END) as active_knowledge_bases,
                    SUM(CASE WHEN kd.status = 0 THEN 1 ELSE 0 END) as inactive_knowledge_bases
                FROM knowledge_database kd
            """
            params = []
        else:
            # 普通用户只能查看自己的统计信息
            sql = """
                SELECT 
                    COUNT(*) as total_knowledge_bases,
                    SUM(CASE WHEN kd.status = 1 THEN 1 ELSE 0 END) as active_knowledge_bases,
                    SUM(CASE WHEN kd.status = 0 THEN 1 ELSE 0 END) as inactive_knowledge_bases
                FROM knowledge_database kd
                WHERE kd.user_id = %s
            """
            params = [user_id]
        
        # 执行查询
        stats_result = execute_query_with_params(sql, params)
        stats = stats_result[0] if stats_result else {}
        
        # 获取向量索引统计信息
        vector_store = VectorStore()
        total_vectors = 0
        total_indexes = 0
        
        if role_id == 1:
            # 管理员查看所有索引
            kb_sql = "SELECT id FROM knowledge_database WHERE status = 1"
            kb_params = []
        else:
            # 普通用户查看自己的索引
            kb_sql = "SELECT id FROM knowledge_database WHERE status = 1 AND user_id = %s"
            kb_params = [user_id]
        
        kb_results = execute_query_with_params(kb_sql, kb_params)
        
        for kb in kb_results:
            index_info = vector_store.get_index_info(kb['id'], user_id=user_id, role_id=role_id)
            if index_info:
                total_indexes += 1
                total_vectors += index_info.get('total_vectors', 0)
        
        # 构建统计信息
        statistics = {
            'knowledge_bases': {
                'total': stats.get('total_knowledge_bases', 0),
                'active': stats.get('active_knowledge_bases', 0),
                'inactive': stats.get('inactive_knowledge_bases', 0)
            },
            'vector_indexes': {
                'total': total_indexes,
                'total_vectors': total_vectors
            },
            'user_info': {
                'user_id': user_id,
                'role_id': role_id,
                'is_admin': role_id == 1
            }
        }
        
        return create_success_response(statistics)
        
    except Exception as e:
        logger.error(f"获取向量统计信息失败: {str(e)}", exc_info=True)
        return create_error_response(f"获取向量统计信息失败: {str(e)}", 500)
