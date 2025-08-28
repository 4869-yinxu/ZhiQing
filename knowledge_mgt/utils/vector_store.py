"""
向量存储模块
用于管理FAISS索引和向量操作，支持用户级别隔离
"""

import os
import json
import logging
import numpy as np
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS未安装，向量存储功能不可用")


class VectorStore:
    """向量存储类，用于管理FAISS索引和向量操作，支持用户级别隔离"""

    def __init__(self, vector_dimension=384, index_type="Flat"):
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS未安装，无法使用向量存储功能")
            
        self.vector_dimension = vector_dimension
        self.index_type = index_type
        # 向量库存储目录
        self.vector_dir = os.path.join(settings.MEDIA_ROOT, 'vector_indexes')
        os.makedirs(self.vector_dir, exist_ok=True)

    def _get_knowledge_db_info(self, knowledge_db_id):
        """获取知识库信息，包括用户权限验证"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT kd.id, kd.name, kd.user_id, kd.vector_dimension, kd.index_type,
                           u.username
                    FROM knowledge_database kd
                    JOIN user u ON kd.user_id = u.id
                    WHERE kd.id = %s
                """, [knowledge_db_id])
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': result[0],
                        'name': result[1],
                        'user_id': result[2],
                        'vector_dimension': result[3],
                        'index_type': result[4],
                        'username': result[5]
                    }
                return None
        except Exception as e:
            logger.error(f"获取知识库信息失败: {str(e)}")
            return None

    def _verify_user_permission(self, knowledge_db_id, user_id, role_id):
        """验证用户对知识库的访问权限"""
        try:
            kb_info = self._get_knowledge_db_info(knowledge_db_id)
            if not kb_info:
                logger.warning(f"知识库 {knowledge_db_id} 不存在")
                return False, "知识库不存在"
            
            # 管理员可以访问所有知识库
            if role_id == 1:
                return True, kb_info
            
            # 普通用户只能访问自己的知识库
            if kb_info['user_id'] != user_id:
                logger.warning(f"用户 {user_id} 无权访问知识库 {knowledge_db_id}（所有者: {kb_info['user_id']}）")
                return False, "无权限访问此知识库"
            
            return True, kb_info
        except Exception as e:
            logger.error(f"验证用户权限失败: {str(e)}")
            return False, "权限验证失败"

    def create_index(self, knowledge_db_id, user_id=None, role_id=None):
        """为知识库创建FAISS索引，包含权限验证"""
        # 如果提供了用户信息，进行权限验证
        if user_id is not None and role_id is not None:
            has_permission, result = self._verify_user_permission(knowledge_db_id, user_id, role_id)
            if not has_permission:
                logger.error(f"创建索引失败: {result}")
                return False
            
            kb_info = result
            # 使用知识库的实际配置
            self.vector_dimension = kb_info['vector_dimension']
            self.index_type = kb_info['index_type']
        
        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        os.makedirs(db_vector_dir, exist_ok=True)

        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")
        metadata_path = os.path.join(db_vector_dir, "metadata.json")

        # 检查索引是否已存在
        if os.path.exists(index_path) and os.path.exists(mapping_path):
            logger.info(f"知识库 {knowledge_db_id} 的索引已存在")
            return True

        try:
            # 创建FAISS索引
            if self.index_type == "Flat":
                index = faiss.IndexFlatL2(self.vector_dimension)
            elif self.index_type == "HNSW":
                # 创建HNSW索引，M是每个节点的最大连接数
                index = faiss.IndexHNSWFlat(self.vector_dimension, 32)
                # 设置HNSW参数
                index.hnsw.efConstruction = 200
                index.hnsw.efSearch = 100
            elif self.index_type == "IVF":
                # 为IVF创建量化器
                quantizer = faiss.IndexFlatL2(self.vector_dimension)
                # 创建IVF索引，nlist是聚类的数量
                index = faiss.IndexIVFFlat(quantizer, self.vector_dimension, 100)
                # IVF索引需要训练
                # 这里需要一些训练数据，通常实际应用中需要真实数据
                # 如果没有训练数据，这里使用随机数据
                random_data = np.random.random((100, self.vector_dimension)).astype('float32')
                index.train(random_data)
            else:
                # 默认使用Flat
                logger.warning(f"不支持的索引类型 {self.index_type}，使用默认Flat")
                index = faiss.IndexFlatL2(self.vector_dimension)

            # 保存索引
            faiss.write_index(index, index_path)

            # 创建空的ID映射
            with open(mapping_path, 'w') as f:
                json.dump({}, f)

            # 创建元数据文件
            metadata = {
                'knowledge_db_id': knowledge_db_id,
                'vector_dimension': self.vector_dimension,
                'index_type': self.index_type,
                'created_at': str(np.datetime64('now')),
                'total_vectors': 0
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"已为知识库 {knowledge_db_id} 创建索引")
            return True
        except Exception as e:
            logger.error(f"创建索引时出错: {str(e)}", exc_info=True)
            return False

    def add_vectors(self, knowledge_db_id, chunk_ids, vectors, user_id=None, role_id=None):
        """添加向量到索引，包含权限验证"""
        # 如果提供了用户信息，进行权限验证
        if user_id is not None and role_id is not None:
            has_permission, result = self._verify_user_permission(knowledge_db_id, user_id, role_id)
            if not has_permission:
                logger.error(f"添加向量失败: {result}")
                return False
        
        if len(chunk_ids) != len(vectors):
            logger.error("分块ID和向量数量不匹配")
            return False

        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")
        metadata_path = os.path.join(db_vector_dir, "metadata.json")

        try:
            # 检查索引是否存在
            if not os.path.exists(index_path) or not os.path.exists(mapping_path):
                self.create_index(knowledge_db_id, user_id, role_id)

            # 读取索引
            index = faiss.read_index(index_path)

            # 读取ID映射
            with open(mapping_path, 'r') as f:
                id_mapping = json.load(f)

            # 将向量添加到索引
            vectors_array = np.array(vectors).astype('float32')
            
            # 检查维度匹配
            if vectors_array.shape[1] != index.d:
                logger.warning(f"向量维度不匹配: 索引维度 {index.d}, 向量维度 {vectors_array.shape[1]}")
                
                # 如果向量维度小于索引维度，用零填充
                if vectors_array.shape[1] < index.d:
                    padding = np.zeros((vectors_array.shape[0], index.d - vectors_array.shape[1]), dtype='float32')
                    vectors_array = np.concatenate([vectors_array, padding], axis=1)
                    logger.info(f"已用零填充向量到维度 {index.d}")
                else:
                    # 如果向量维度大于索引维度，截断
                    vectors_array = vectors_array[:, :index.d]
                    logger.info(f"已截断向量到维度 {index.d}")
            
            vector_ids = list(range(index.ntotal, index.ntotal + len(vectors)))

            index.add(vectors_array)

            # 更新ID映射
            for i, chunk_id in enumerate(chunk_ids):
                id_mapping[str(vector_ids[i])] = chunk_id

            # 保存更新后的索引和映射
            faiss.write_index(index, index_path)
            with open(mapping_path, 'w') as f:
                json.dump(id_mapping, f)

            # 更新元数据
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                metadata['total_vectors'] = index.ntotal
                metadata['last_updated'] = str(np.datetime64('now'))
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

            logger.info(f"已将 {len(vectors)} 个向量添加到知识库 {knowledge_db_id} 的索引")
            return vector_ids
        except Exception as e:
            logger.error(f"添加向量时出错: {str(e)}", exc_info=True)
            return []

    def search(self, knowledge_db_id, query_vector, top_k=5, user_id=None, role_id=None, use_cosine=False):
        """搜索最相似的向量，包含权限验证"""
        # 如果提供了用户信息，进行权限验证
        if user_id is not None and role_id is not None:
            has_permission, result = self._verify_user_permission(knowledge_db_id, user_id, role_id)
            if not has_permission:
                logger.error(f"向量搜索失败: {result}")
                return []

        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")

        try:
            if not os.path.exists(index_path) or not os.path.exists(mapping_path):
                logger.warning(f"知识库 {knowledge_db_id} 的索引不存在")
                return []

            # 读取索引
            index = faiss.read_index(index_path)

            # 读取ID映射
            with open(mapping_path, 'r') as f:
                id_mapping = json.load(f)

            # 确保query_vector是正确的形状
            query_vector = np.array([query_vector]).astype('float32')

            # 检查维度匹配
            logger.debug(f"索引维度: {index.d}, 查询向量维度: {query_vector.shape[1]}, 配置维度: {self.vector_dimension}")

            # 如果维度不匹配，进行调整
            if query_vector.shape[1] != index.d:
                if query_vector.shape[1] < index.d:
                    # 如果查询向量维度小于索引维度，用零填充
                    padding = np.zeros((1, index.d - query_vector.shape[1]), dtype='float32')
                    query_vector = np.concatenate([query_vector, padding], axis=1)
                else:
                    # 如果查询向量维度大于索引维度，截断
                    query_vector = query_vector[:, :index.d]

            results = []

            if use_cosine:
                # 余弦相似：重构全部向量做归一化，然后与查询向量点积
                # 归一化查询向量
                q = query_vector[0]
                q_norm = np.linalg.norm(q)
                if q_norm == 0:
                    return []
                q = q / q_norm

                # 遍历索引内所有向量并计算相似度
                sims = []
                for vid_str, chunk_id in id_mapping.items():
                    vid = int(vid_str)
                    try:
                        v = index.reconstruct(vid)
                    except Exception:
                        # 某些索引可能不支持reconstruct，跳过
                        continue
                    v_norm = np.linalg.norm(v)
                    if v_norm == 0:
                        sim = 0.0
                    else:
                        sim = float(np.dot(q, v / v_norm))
                    sims.append((sim, chunk_id))

                # 取TopK（相似度从高到低）
                sims.sort(key=lambda x: x[0], reverse=True)
                for i, (sim, chunk_id) in enumerate(sims[:top_k]):
                    # 余弦相似度模式下，distance直接使用相似度值
                    results.append({
                        'chunk_id': chunk_id,
                        'distance': float(sim),
                        'rank': i + 1
                    })
            else:
                # FAISS原生L2检索
                distances, indices = index.search(query_vector, top_k)
                for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                    if idx != -1:  # FAISS返回-1表示无效结果
                        chunk_id = id_mapping.get(str(idx))
                        if chunk_id:
                            results.append({
                                'chunk_id': chunk_id,
                                'distance': float(distance),
                                'rank': i + 1
                            })

            logger.info(f"在知识库 {knowledge_db_id} 中找到 {len(results)} 个相似结果")
            return results

        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}", exc_info=True)
            return []

    def delete_vectors(self, knowledge_db_id, vector_ids, user_id=None, role_id=None):
        """删除指定的向量，包含权限验证"""
        # 如果提供了用户信息，进行权限验证
        if user_id is not None and role_id is not None:
            has_permission, result = self._verify_user_permission(knowledge_db_id, user_id, role_id)
            if not has_permission:
                logger.error(f"删除向量失败: {result}")
                return False

        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")
        metadata_path = os.path.join(db_vector_dir, "metadata.json")

        try:
            if not os.path.exists(index_path) or not os.path.exists(mapping_path):
                logger.warning(f"知识库 {knowledge_db_id} 的索引不存在")
                return False

            # 读取索引
            index = faiss.read_index(index_path)

            # 读取ID映射
            with open(mapping_path, 'r') as f:
                id_mapping = json.load(f)

            # 创建新的索引（FAISS不支持直接删除向量）
            if self.index_type == "Flat":
                new_index = faiss.IndexFlatL2(self.vector_dimension)
            elif self.index_type == "HNSW":
                new_index = faiss.IndexHNSWFlat(self.vector_dimension, 32)
                new_index.hnsw.efConstruction = 200
                new_index.hnsw.efSearch = 100
            else:
                new_index = faiss.IndexFlatL2(self.vector_dimension)

            # 重新构建索引，排除要删除的向量
            remaining_vectors = []
            new_mapping = {}
            new_vector_id = 0

            for old_vector_id, chunk_id in id_mapping.items():
                if old_vector_id not in [str(vid) for vid in vector_ids]:
                    # 获取原向量
                    old_vector = index.reconstruct(int(old_vector_id))
                    remaining_vectors.append(old_vector)
                    new_mapping[str(new_vector_id)] = chunk_id
                    new_vector_id += 1

            # 添加剩余向量到新索引
            if remaining_vectors:
                vectors_array = np.array(remaining_vectors).astype('float32')
                new_index.add(vectors_array)

            # 保存新索引和映射
            faiss.write_index(new_index, index_path)
            with open(mapping_path, 'w') as f:
                json.dump(new_mapping, f)

            # 更新元数据
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                metadata['total_vectors'] = new_index.ntotal
                metadata['last_updated'] = str(np.datetime64('now'))
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

            logger.info(f"已从知识库 {knowledge_db_id} 删除 {len(vector_ids)} 个向量")
            return True

        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}", exc_info=True)
            return False

    def get_index_info(self, knowledge_db_id, user_id=None, role_id=None):
        """获取索引信息，包含权限验证"""
        # 如果提供了用户信息，进行权限验证
        if user_id is not None and role_id is not None:
            has_permission, result = self._verify_user_permission(knowledge_db_id, user_id, role_id)
            if not has_permission:
                logger.error(f"获取索引信息失败: {result}")
                return None

        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")
        metadata_path = os.path.join(db_vector_dir, "metadata.json")

        try:
            if not os.path.exists(index_path):
                return None

            # 读取索引
            index = faiss.read_index(index_path)

            # 读取映射
            id_mapping = {}
            if os.path.exists(mapping_path):
                with open(mapping_path, 'r') as f:
                    id_mapping = json.load(f)

            # 读取元数据
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

            return {
                'knowledge_db_id': knowledge_db_id,
                'index_type': self.index_type,
                'vector_dimension': index.d,
                'total_vectors': index.ntotal,
                'mapping_count': len(id_mapping),
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"获取索引信息失败: {str(e)}")
            return None

    def rebuild_index(self, knowledge_db_id, vectors_data, user_id=None, role_id=None):
        """重建索引，包含权限验证"""
        # 如果提供了用户信息，进行权限验证
        if user_id is not None and role_id is not None:
            has_permission, result = self._verify_user_permission(knowledge_db_id, user_id, role_id)
            if not has_permission:
                logger.error(f"重建索引失败: {result}")
                return False

        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        os.makedirs(db_vector_dir, exist_ok=True)
        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")
        metadata_path = os.path.join(db_vector_dir, "metadata.json")

        try:
            # 创建新索引
            if self.index_type == "Flat":
                index = faiss.IndexFlatL2(self.vector_dimension)
            elif self.index_type == "HNSW":
                index = faiss.IndexHNSWFlat(self.vector_dimension, 32)
                index.hnsw.efConstruction = 200
                index.hnsw.efSearch = 100
            elif self.index_type == "IVF":
                quantizer = faiss.IndexFlatL2(self.vector_dimension)
                index = faiss.IndexIVFFlat(quantizer, self.vector_dimension, 100)
                # 训练索引
                if vectors_data:
                    training_vectors = np.array(vectors_data[:100]).astype('float32')
                    index.train(training_vectors)
            else:
                index = faiss.IndexFlatL2(self.vector_dimension)

            # 添加所有向量
            if vectors_data:
                vectors_array = np.array(vectors_data).astype('float32')
                index.add(vectors_array)

            # 保存索引
            faiss.write_index(index, index_path)

            # 创建ID映射
            id_mapping = {str(i): i for i in range(len(vectors_data))}
            with open(mapping_path, 'w') as f:
                json.dump(id_mapping, f)

            # 更新元数据
            metadata = {
                'knowledge_db_id': knowledge_db_id,
                'vector_dimension': self.vector_dimension,
                'index_type': self.index_type,
                'created_at': str(np.datetime64('now')),
                'total_vectors': len(vectors_data),
                'last_updated': str(np.datetime64('now'))
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"已重建知识库 {knowledge_db_id} 的索引，包含 {len(vectors_data)} 个向量")
            return True

        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}", exc_info=True)
            return False

    def cleanup_index(self, knowledge_db_id, user_id=None, role_id=None):
        """清理索引，包含权限验证"""
        # 如果提供了用户信息，进行权限验证
        if user_id is not None and role_id is not None:
            has_permission, result = self._verify_user_permission(knowledge_db_id, user_id, role_id)
            if not has_permission:
                logger.error(f"清理索引失败: {result}")
                return False

        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        
        try:
            if os.path.exists(db_vector_dir):
                import shutil
                shutil.rmtree(db_vector_dir)
                logger.info(f"已清理知识库 {knowledge_db_id} 的索引目录")
                return True
            else:
                logger.info(f"知识库 {knowledge_db_id} 的索引目录不存在")
                return True
        except Exception as e:
            logger.error(f"清理索引失败: {str(e)}")
            return False
