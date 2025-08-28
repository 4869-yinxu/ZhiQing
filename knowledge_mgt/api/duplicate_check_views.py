#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
知识查重看板API视图
提供知识片段的查重与溯源功能
"""

import os
import logging
import json
import numpy as np
from typing import List, Dict, Any, Optional
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.conf import settings

from zhiqing_server.utils.response_code import ResponseCode
from zhiqing_server.utils.auth_utils import jwt_required, get_user_from_request
from ..utils.embeddings import local_embedding_manager
from ..utils.vector_store import VectorStore

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def check_duplicate_content(request):
    """检查内容重复性API"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 获取请求参数
        content = request.POST.get('content', '').strip()
        knowledge_id = request.POST.get('knowledge_id')
        similarity_threshold = float(request.POST.get('similarity_threshold', 0.8))
        top_k = int(request.POST.get('top_k', 10))
        
        if not content or not knowledge_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="缺少必要参数：content 或 knowledge_id"),
                status=400
            )
        
        # 验证知识库权限
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, vector_dimension, index_type 
                FROM knowledge_database 
                WHERE id = %s
            """, [knowledge_id])
            
            kb_info = cursor.fetchone()
            if not kb_info:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库不存在"),
                    status=404
                )
            
            # 检查用户权限
            if role_id != 1:  # 非管理员
                cursor.execute("""
                    SELECT id FROM knowledge_database 
                    WHERE id = %s AND user_id = %s
                """, [knowledge_id, user_id])
                
                if not cursor.fetchone():
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message="无权限访问该知识库"),
                        status=403
                    )
        
        # 获取嵌入模型
        embedding_model = local_embedding_manager.get_current_model()
        if embedding_model is None:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="没有加载的嵌入模型，请先在系统管理中加载嵌入模型"),
                status=500
            )
        
        # 将查询内容转换为向量
        query_vector = embedding_model.embed_text(content)
        
        # 初始化向量存储
        vector_store = VectorStore(
            vector_dimension=embedding_model.get_dimension(), 
            index_type=kb_info[3]
        )
        
        # 搜索相似内容
        similar_chunks = vector_store.search(
            knowledge_id, 
            query_vector, 
            top_k=top_k,
            user_id=user_id,
            role_id=role_id
        )
        
        # 分析重复内容
        duplicate_analysis = []
        for chunk in similar_chunks:
            distance = chunk['distance']
            similarity_score = 1.0 / (1.0 + distance) if distance >= 0 else 0.0
            
            if similarity_score >= similarity_threshold:
                # 获取详细信息
                chunk_info = get_chunk_details(chunk['chunk_id'], user_id, role_id)
                if chunk_info:
                    duplicate_analysis.append({
                        'chunk_id': chunk['chunk_id'],
                        'similarity_score': round(similarity_score, 4),
                        'distance': round(distance, 4),
                        'rank': chunk['rank'],
                        'content': chunk_info['content'],
                        'document_info': chunk_info['document_info'],
                        'duplicate_type': classify_duplicate_type(similarity_score),
                        'risk_level': assess_risk_level(similarity_score)
                    })
        
        # 统计信息
        stats = {
            'total_chunks_checked': len(similar_chunks),
            'duplicate_chunks_found': len(duplicate_analysis),
            'duplicate_ratio': round(len(duplicate_analysis) / len(similar_chunks), 4) if similar_chunks else 0,
            'highest_similarity': max([item['similarity_score'] for item in duplicate_analysis]) if duplicate_analysis else 0,
            'average_similarity': round(np.mean([item['similarity_score'] for item in duplicate_analysis]), 4) if duplicate_analysis else 0
        }
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
            'duplicate_analysis': duplicate_analysis,
            'statistics': stats,
            'query_content': content,
            'knowledge_base': {
                'id': kb_info[0],
                'name': kb_info[1]
            }
        }))
        
    except Exception as e:
        logger.error(f"检查内容重复性失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"检查失败: {str(e)}"),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def batch_check_duplicates(request):
    """批量检查重复内容API - 优化版本"""
    try:
        logger.info("开始批量查重请求")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 获取请求参数
        knowledge_id = request.POST.get('knowledge_id')
        similarity_threshold = float(request.POST.get('similarity_threshold', 0.8))
        min_chunk_size = int(request.POST.get('min_chunk_size', 50))
        max_results = int(request.POST.get('max_results', 100))
        
        logger.info(f"批量查重参数: knowledge_id={knowledge_id}, threshold={similarity_threshold}, min_size={min_chunk_size}, max_results={max_results}")
        
        if not knowledge_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="缺少必要参数：knowledge_id"),
                status=400
            )
        
        # 验证知识库权限
        logger.info("验证知识库权限...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, vector_dimension, index_type 
                FROM knowledge_database 
                WHERE id = %s
            """, [knowledge_id])
            
            kb_info = cursor.fetchone()
            if not kb_info:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库不存在"),
                    status=404
                )
            
            # 检查用户权限
            if role_id != 1:  # 非管理员
                cursor.execute("""
                    SELECT id FROM knowledge_database 
                    WHERE id = %s AND user_id = %s
                """, [knowledge_id, user_id])
                
                if not cursor.fetchone():
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message="无权限访问该知识库"),
                        status=403
                    )
        
        # 获取知识库中的所有分块
        logger.info("获取知识库分块...")
        chunks = get_knowledge_base_chunks(knowledge_id, user_id, role_id, min_chunk_size)
        
        if not chunks:
            logger.info("知识库中没有分块，返回空结果")
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(data={
                    'duplicate_groups': [],
                    'statistics': {
                        'total_chunks': 0,
                        'duplicate_groups': 0,
                        'duplicate_chunks': 0
                    }
                })
            )
        
        logger.info(f"获取到 {len(chunks)} 个分块")
        
        # 获取嵌入模型 - 优先使用知识库绑定的模型
        logger.info("获取嵌入模型...")
        embedding_model = None
        
        # 检查知识库是否绑定了嵌入模型
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT embedding_model_id FROM knowledge_database WHERE id = %s
            """, [knowledge_id])
            result = cursor.fetchone()
            embedding_model_id = result[0] if result else None
        
        if embedding_model_id:
            logger.info(f"知识库绑定了嵌入模型: {embedding_model_id}")
            try:
                from system_mgt.utils.llms_manager import llms_manager
                from knowledge_mgt.utils.embeddings import get_embedding_model_by_id
                
                # 获取模型配置
                model_config = get_embedding_model_by_id(embedding_model_id)
                if model_config:
                    # 加载模型
                    ok = llms_manager.ensure_knowledge_base_model_loaded(knowledge_id, model_config)
                    if ok:
                        llms_manager.set_active_knowledge_base(knowledge_id)
                        embedding_model = llms_manager.get_current_embed_model()
                        logger.info("成功加载知识库绑定的嵌入模型")
                    else:
                        logger.warning("加载知识库绑定的嵌入模型失败，回退到本地模型")
                else:
                    logger.warning("知识库绑定的嵌入模型配置不存在，回退到本地模型")
            except Exception as e:
                logger.warning(f"加载知识库绑定的嵌入模型异常: {e}，回退到本地模型")
        
        # 如果没有绑定模型或加载失败，尝试使用本地模型
        if embedding_model is None:
            logger.info("尝试使用本地嵌入模型")
            
            # 检查是否有可用的本地模型配置
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, model_type, api_type, model_name, local_path, vector_dimension
                        FROM embedding_model 
                        WHERE api_type = 'local' AND is_active = 1
                        ORDER BY id DESC
                        LIMIT 1
                    """)
                    local_model_row = cursor.fetchone()
                    
                    if local_model_row:
                        local_model_id = local_model_row[0]
                        local_model_name = local_model_row[1]
                        logger.info(f"找到本地模型配置: {local_model_name} (ID: {local_model_id})")
                        
                        # 尝试加载本地模型
                        try:
                            local_model_config = get_embedding_model_by_id(local_model_id)
                            if local_model_config:
                                embedding_model = local_embedding_manager.load_model(local_model_id, local_model_config)
                                logger.info(f"成功加载本地嵌入模型: {local_model_name}")
                            else:
                                logger.warning("本地模型配置获取失败")
                        except Exception as e:
                            logger.error(f"加载本地嵌入模型失败: {e}")
                    else:
                        logger.warning("未找到可用的本地模型配置")
                        
            except Exception as e:
                logger.error(f"查询本地模型配置失败: {e}")
        
        # 如果仍然没有可用的嵌入模型，返回错误
        if embedding_model is None:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="没有可用的嵌入模型，请先在系统管理中配置并加载嵌入模型"),
                status=500
            )
        
        # 批量检查重复
        logger.info("开始批量查重...")
        duplicate_groups = find_duplicate_groups(
            chunks, 
            embedding_model, 
            similarity_threshold,
            max_results
        )
        
        # 统计信息
        total_duplicate_chunks = sum(len(group) for group in duplicate_groups)
        stats = {
            'total_chunks': len(chunks),
            'duplicate_groups': len(duplicate_groups),
            'duplicate_chunks': total_duplicate_chunks,
            'duplicate_ratio': round(total_duplicate_chunks / len(chunks), 4) if chunks else 0
        }
        
        logger.info(f"批量查重完成，统计: {stats}")
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
            'duplicate_groups': duplicate_groups,
            'statistics': stats
        }))
        
    except Exception as e:
        logger.error(f"批量检查重复内容失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"批量检查失败: {str(e)}"),
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_duplicate_statistics(request):
    """获取重复内容统计信息API"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        knowledge_id = request.GET.get('knowledge_id')
        
        if not knowledge_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="缺少必要参数：knowledge_id"),
                status=400
            )
        
        # 验证知识库权限
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name FROM knowledge_database 
                WHERE id = %s
            """, [knowledge_id])
            
            kb_info = cursor.fetchone()
            if not kb_info:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库不存在"),
                    status=404
                )
            
            # 检查用户权限
            if role_id != 1:  # 非管理员
                cursor.execute("""
                    SELECT id FROM knowledge_database 
                    WHERE id = %s AND user_id = %s
                """, [knowledge_id, user_id])
                
                if not cursor.fetchone():
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message="无权限访问该知识库"),
                        status=403
                    )
        
        # 获取统计信息
        stats = get_duplicate_statistics_for_kb(knowledge_id, user_id, role_id)
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
            'knowledge_base': {
                'id': kb_info[0],
                'name': kb_info[1]
            },
            'statistics': stats
        }))
        
    except Exception as e:
        logger.error(f"获取重复内容统计信息失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取统计信息失败: {str(e)}"),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def trace_content_source(request):
    """追踪内容溯源API"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 获取请求参数
        content = request.POST.get('content', '').strip()
        knowledge_id = request.POST.get('knowledge_id')
        search_scope = request.POST.get('search_scope', 'current')  # current, all, external
        
        if not content or not knowledge_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="缺少必要参数：content 或 knowledge_id"),
                status=400
            )
        
        # 验证知识库权限
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name FROM knowledge_database 
                WHERE id = %s
            """, [knowledge_id])
            
            kb_info = cursor.fetchone()
            if not kb_info:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库不存在"),
                    status=404
                )
            
            # 检查用户权限
            if role_id != 1:  # 非管理员
                cursor.execute("""
                    SELECT id FROM knowledge_database 
                    WHERE id = %s AND user_id = %s
                """, [knowledge_id, user_id])
                
                if not cursor.fetchone():
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message="无权限访问该知识库"),
                        status=403
                    )
        
        # 执行溯源搜索
        source_trace = trace_content_sources(
            content, 
            knowledge_id, 
            search_scope, 
            user_id, 
            role_id
        )
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
            'source_trace': source_trace,
            'query_content': content,
            'search_scope': search_scope,
            'knowledge_base': {
                'id': kb_info[0],
                'name': kb_info[1]
            }
        }))
        
    except Exception as e:
        logger.error(f"追踪内容溯源失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"溯源追踪失败: {str(e)}"),
            status=500
        )


# 辅助函数
def get_chunk_details(chunk_id: int, user_id: int, role_id: int) -> Optional[Dict]:
    """获取分块详细信息"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c.id, c.content, c.chunk_index, c.create_time,
                    d.id as document_id, d.filename, d.file_path, d.file_type,
                    d.chunking_method, d.chunk_size, d.user_id as doc_user_id,
                    u.username as doc_username
                FROM knowledge_document_chunk c
                JOIN knowledge_document d ON c.document_id = d.id
                LEFT JOIN account_user u ON d.user_id = u.id
                WHERE c.id = %s
            """, [chunk_id])
            
            chunk_info = cursor.fetchone()
            if not chunk_info:
                return None
            
            # 检查权限
            if role_id != 1 and chunk_info[9] != user_id:
                return None
            
            return {
                'chunk_id': chunk_info[0],
                'content': chunk_info[1],
                'chunk_index': chunk_info[2],
                'create_time': chunk_info[3].isoformat() if chunk_info[3] else None,
                'document_info': {
                    'id': chunk_info[4],
                    'filename': chunk_info[5],
                    'file_path': chunk_info[6],
                    'file_type': chunk_info[7],
                    'chunking_method': chunk_info[8],
                    'chunk_size': chunk_info[9],
                    'user_id': chunk_info[10],
                    'username': chunk_info[11]
                }
            }
    except Exception as e:
        logger.error(f"获取分块详细信息失败: {str(e)}")
        return None


def classify_duplicate_type(similarity_score: float) -> str:
    """分类重复类型"""
    if similarity_score >= 0.95:
        return "exact_duplicate"  # 完全重复
    elif similarity_score >= 0.85:
        return "high_similarity"  # 高度相似
    elif similarity_score >= 0.75:
        return "moderate_similarity"  # 中度相似
    elif similarity_score >= 0.65:
        return "low_similarity"  # 低度相似
    else:
        return "minimal_similarity"  # 最小相似


def assess_risk_level(similarity_score: float) -> str:
    """评估风险等级"""
    if similarity_score >= 0.95:
        return "critical"  # 严重风险
    elif similarity_score >= 0.85:
        return "high"  # 高风险
    elif similarity_score >= 0.75:
        return "medium"  # 中等风险
    elif similarity_score >= 0.65:
        return "low"  # 低风险
    else:
        return "minimal"  # 最小风险


def get_knowledge_base_chunks(knowledge_id: int, user_id: int, role_id: int, min_chunk_size: int) -> List[Dict]:
    """获取知识库中的所有分块"""
    try:
        with connection.cursor() as cursor:
            # 构建权限查询
            if role_id == 1:  # 管理员
                cursor.execute("""
                    SELECT 
                        c.id, c.content, c.chunk_index,
                        d.id as document_id, d.filename
                    FROM knowledge_document_chunk c
                    JOIN knowledge_document d ON c.document_id = d.id
                    WHERE c.database_id = %s AND LENGTH(c.content) >= %s
                    ORDER BY c.id
                """, [knowledge_id, min_chunk_size])
            else:  # 普通用户
                cursor.execute("""
                    SELECT 
                        c.id, c.content, c.chunk_index,
                        d.id as document_id, d.filename
                    FROM knowledge_document_chunk c
                    JOIN knowledge_document d ON c.document_id = d.id
                    WHERE c.database_id = %s AND d.user_id = %s AND LENGTH(c.content) >= %s
                    ORDER BY c.id
                """, [knowledge_id, user_id, min_chunk_size])
            
            chunks = []
            for row in cursor.fetchall():
                chunks.append({
                    'id': row[0],
                    'content': row[1],
                    'chunk_index': row[2],
                    'document_id': row[3],
                    'filename': row[4]
                })
            
            return chunks
    except Exception as e:
        logger.error(f"获取知识库分块失败: {str(e)}")
        return []


def find_duplicate_groups(chunks: List[Dict], embedding_model, similarity_threshold: float, max_results: int) -> List[List[Dict]]:
    """查找重复组 - 优化版本"""
    if len(chunks) < 2:
        return []
    
    logger.info(f"开始批量查重，共 {len(chunks)} 个分块，阈值: {similarity_threshold}")
    
    # 批量生成所有分块的向量，避免重复调用
    logger.info("批量生成向量...")
    chunk_vectors = {}
    
    # 检查嵌入模型类型，使用正确的方法
    if hasattr(embedding_model, 'get_text_embedding'):
        # LlamaIndex 模型
        embed_method = embedding_model.get_text_embedding
    elif hasattr(embedding_model, 'embed_text'):
        # 本地模型
        embed_method = embedding_model.embed_text
    else:
        logger.error("嵌入模型不支持文本向量化")
        return []
    
    for chunk in chunks:
        try:
            vector = embed_method(chunk['content'])
            chunk_vectors[chunk['id']] = vector
        except Exception as e:
            logger.error(f"生成向量失败，分块ID: {chunk['id']}, 错误: {e}")
            continue
    
    logger.info(f"成功生成 {len(chunk_vectors)} 个向量")
    
    duplicate_groups = []
    processed_chunks = set()
    
    # 使用更高效的比较策略
    chunk_items = list(chunk_vectors.items())
    for i, (chunk_id1, vector1) in enumerate(chunk_items):
        if chunk_id1 in processed_chunks:
            continue
        
        # 找到对应的chunk对象
        chunk1 = next((c for c in chunks if c['id'] == chunk_id1), None)
        if not chunk1:
            continue
            
        current_group = [chunk1]
        processed_chunks.add(chunk_id1)
        
        # 比较与其他向量的相似度
        for j, (chunk_id2, vector2) in enumerate(chunk_items[i+1:], i+1):
            if chunk_id2 in processed_chunks:
                continue
            
            # 计算相似度
            similarity = calculate_cosine_similarity(vector1, vector2)
            
            if similarity >= similarity_threshold:
                chunk2 = next((c for c in chunks if c['id'] == chunk_id2), None)
                if chunk2:
                    current_group.append(chunk2)
                    processed_chunks.add(chunk_id2)
        
        # 只保留有重复的组
        if len(current_group) > 1:
            duplicate_groups.append(current_group)
            logger.info(f"发现重复组 {len(duplicate_groups)}: {len(current_group)} 个分块")
            
            # 限制结果数量
            if len(duplicate_groups) >= max_results:
                logger.info(f"达到最大结果数限制: {max_results}")
                break
    
    logger.info(f"批量查重完成，共发现 {len(duplicate_groups)} 个重复组")
    return duplicate_groups


def calculate_cosine_similarity(vector1, vector2) -> float:
    """计算余弦相似度"""
    try:
        # 确保向量是numpy数组
        v1 = np.array(vector1).flatten()
        v2 = np.array(vector2).flatten()
        
        # 计算余弦相似度
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return dot_product / (norm_v1 * norm_v2)
    except Exception as e:
        logger.error(f"计算余弦相似度失败: {str(e)}")
        return 0.0


def get_duplicate_statistics_for_kb(knowledge_id: int, user_id: int, role_id: int) -> Dict:
    """获取知识库的重复内容统计信息"""
    try:
        with connection.cursor() as cursor:
            # 获取基本统计信息
            if role_id == 1:  # 管理员
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_chunks,
                        COUNT(DISTINCT document_id) as total_documents,
                        AVG(LENGTH(content)) as avg_chunk_size
                    FROM knowledge_document_chunk 
                    WHERE database_id = %s
                """, [knowledge_id])
            else:  # 普通用户
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_chunks,
                        COUNT(DISTINCT d.id) as total_documents,
                        AVG(LENGTH(c.content)) as avg_chunk_size
                    FROM knowledge_document_chunk c
                    JOIN knowledge_document d ON c.document_id = d.id
                    WHERE c.database_id = %s AND d.user_id = %s
                """, [knowledge_id, user_id])
            
            basic_stats = cursor.fetchone()
            
            # 获取重复内容统计（基于内容长度相似性）
            if role_id == 1:  # 管理员
                cursor.execute("""
                    SELECT 
                        LENGTH(content) as content_length,
                        COUNT(*) as count
                    FROM knowledge_document_chunk 
                    WHERE database_id = %s
                    GROUP BY LENGTH(content)
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 10
                """, [knowledge_id])
            else:  # 普通用户
                cursor.execute("""
                    SELECT 
                        LENGTH(c.content) as content_length,
                        COUNT(*) as count
                    FROM knowledge_document_chunk c
                    JOIN knowledge_document d ON c.document_id = d.id
                    WHERE c.database_id = %s AND d.user_id = %s
                    GROUP BY LENGTH(c.content)
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 10
                """, [knowledge_id, user_id])
            
            duplicate_stats = cursor.fetchall()
            
            return {
                'total_chunks': basic_stats[0] if basic_stats else 0,
                'total_documents': basic_stats[1] if basic_stats else 0,
                'average_chunk_size': round(basic_stats[2], 2) if basic_stats and basic_stats[2] else 0,
                'potential_duplicates': [
                    {
                        'content_length': row[0],
                        'count': row[1]
                    } for row in duplicate_stats
                ]
            }
    except Exception as e:
        logger.error(f"获取重复内容统计信息失败: {str(e)}")
        return {}


def trace_content_sources(content: str, knowledge_id: int, search_scope: str, user_id: int, role_id: int) -> List[Dict]:
    """追踪内容溯源"""
    try:
        # 获取嵌入模型
        embedding_model = local_embedding_manager.get_current_model()
        if embedding_model is None:
            return []
        
        # 将查询内容转换为向量
        query_vector = embedding_model.embed_text(content)
        
        # 根据搜索范围确定搜索的知识库
        search_kb_ids = [knowledge_id]
        
        if search_scope == 'all':
            # 搜索所有有权限的知识库
            with connection.cursor() as cursor:
                if role_id == 1:  # 管理员
                    cursor.execute("SELECT id FROM knowledge_database")
                else:  # 普通用户
                    cursor.execute("SELECT id FROM knowledge_database WHERE user_id = %s", [user_id])
                
                search_kb_ids = [row[0] for row in cursor.fetchall()]
        
        # 在所有相关知识库中搜索
        all_sources = []
        for kb_id in search_kb_ids:
            try:
                # 获取知识库信息
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, vector_dimension, index_type 
                        FROM knowledge_database 
                        WHERE id = %s
                    """, [kb_id])
                    
                    kb_info = cursor.fetchone()
                    if not kb_info:
                        continue
                
                # 初始化向量存储
                vector_store = VectorStore(
                    vector_dimension=embedding_model.get_dimension(), 
                    index_type=kb_info[3]
                )
                
                # 搜索相似内容
                similar_chunks = vector_store.search(
                    kb_id, 
                    query_vector, 
                    top_k=5,
                    user_id=user_id,
                    role_id=role_id
                )
                
                # 处理搜索结果
                for chunk in similar_chunks:
                    distance = chunk['distance']
                    similarity_score = 1.0 / (1.0 + distance) if distance >= 0 else 0.0
                    
                    if similarity_score >= 0.6:  # 降低阈值以获取更多溯源信息
                        chunk_info = get_chunk_details(chunk['chunk_id'], user_id, role_id)
                        if chunk_info:
                            all_sources.append({
                                'knowledge_base_id': kb_id,
                                'knowledge_base_name': kb_info[1],
                                'chunk_id': chunk['chunk_id'],
                                'similarity_score': round(similarity_score, 4),
                                'content': chunk_info['content'],
                                'document_info': chunk_info['document_info'],
                                'source_type': 'internal' if kb_id == knowledge_id else 'external'
                            })
            
            except Exception as e:
                logger.error(f"在知识库 {kb_id} 中搜索溯源失败: {str(e)}")
                continue
        
        # 按相似度排序
        all_sources.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return all_sources[:20]  # 限制返回结果数量
        
    except Exception as e:
        logger.error(f"追踪内容溯源失败: {str(e)}")
        return []
