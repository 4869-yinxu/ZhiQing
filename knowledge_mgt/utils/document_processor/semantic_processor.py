#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语义分块处理器
基于嵌入模型的智能语义分块
"""

import re
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from .legacy_processor import LegacyDocumentProcessor

logger = logging.getLogger(__name__)


class SemanticProcessor(LegacyDocumentProcessor):
    """专门的语义分块处理器"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config or {})
        self.semantic_config = self._init_semantic_config()
        self.embedding_model = None
        self._initialize_models()
        
    def _init_semantic_config(self) -> Dict:
        """初始化语义分块配置"""
        return {
            'similarity_threshold': self.config.get('similarity_threshold', 0.7),
            'semantic_weight': self.config.get('semantic_weight', 0.7),
            'lexical_weight': self.config.get('lexical_weight', 0.2),
            'structural_weight': self.config.get('structural_weight', 0.1),
            'use_embeddings': self.config.get('use_embeddings', True),
            'max_chunk_sentences': self.config.get('max_chunk_sentences', 10),
            'adaptive_threshold': self.config.get('adaptive_threshold', True)
        }
    
    def _initialize_models(self):
        """初始化嵌入模型配置（不立即加载）"""
        # 保存模型配置，但不立即加载
        self.embedding_model_config = {
            'model_name': self.config.get('embedding_model', 'paraphrase-multilingual-MiniLM-L12-v2')
        }
        logger.info(f"嵌入模型配置已保存，将在需要时按需加载: {self.embedding_model_config['model_name']}")
    
    def _ensure_embedding_model_loaded(self):
        """确保嵌入模型已加载（按需加载）"""
        if self.embedding_model is not None:
            return True
        
        if not self.semantic_config['use_embeddings']:
            return False
        
        try:
            from sentence_transformers import SentenceTransformer
            model_name = self.embedding_model_config['model_name']
            logger.info(f"按需加载嵌入模型: {model_name}")
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"嵌入模型加载成功: {model_name}")
            return True
        except ImportError:
            logger.warning("sentence-transformers未安装，使用基础语义分块")
            self.semantic_config['use_embeddings'] = False
            return False
        except Exception as e:
            logger.warning(f"嵌入模型加载失败: {e}")
            self.semantic_config['use_embeddings'] = False
            return False
    
    def split_text(self, text: str) -> List[str]:
        """语义分块主方法"""
        logger.info("开始语义分块处理")
        
        # 预处理文本
        sentences = self._preprocess_text(text)
        
        if len(sentences) <= 1:
            return sentences
        
        # 计算句子嵌入
        sentence_embeddings = self._compute_sentence_embeddings(sentences)
        
        # 语义分块
        chunks = self._semantic_chunking(sentences, sentence_embeddings)
        
        logger.info(f"语义分块完成，共生成 {len(chunks)} 个分块")
        return chunks
    
    def _preprocess_text(self, text: str) -> List[str]:
        """预处理文本，分割句子"""
        # 中英文句子分割
        sentence_patterns = [
            r'[.!?。！？；;]\s*',  # 英文和中文标点
            r'[\n\r]+',           # 换行符
        ]
        
        sentences = re.split(sentence_patterns[0], text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 处理长句子
        refined_sentences = []
        for sentence in sentences:
            if len(sentence) > 200:
                sub_sentences = re.split(r'[，,；;]\s*', sentence)
                refined_sentences.extend([s.strip() for s in sub_sentences if s.strip()])
            else:
                refined_sentences.append(sentence)
        
        return refined_sentences
    
    def _compute_sentence_embeddings(self, sentences: List[str]) -> Optional[np.ndarray]:
        """计算句子嵌入向量"""
        if not self.semantic_config['use_embeddings']:
            return None
        
        # 确保模型已加载
        if not self._ensure_embedding_model_loaded():
            return None
        
        try:
            valid_sentences = [s for s in sentences if s.strip()]
            if not valid_sentences:
                return None
            
            embeddings = self.embedding_model.encode(valid_sentences, convert_to_tensor=False)
            return embeddings
            
        except Exception as e:
            logger.warning(f"计算句子嵌入失败: {e}")
            return None
    
    def _semantic_chunking(self, sentences: List[str], embeddings: Optional[np.ndarray]) -> List[str]:
        """基于语义的分块算法"""
        chunks = []
        current_chunk = [sentences[0]]
        current_embeddings = [embeddings[0]] if embeddings is not None else None
        
        for i in range(1, len(sentences)):
            sentence = sentences[i]
            sentence_embedding = embeddings[i] if embeddings is not None else None
            
            # 判断是否合并
            should_merge = self._should_merge_sentence(
                current_chunk, sentence, current_embeddings, sentence_embedding
            )
            
            if should_merge:
                current_chunk.append(sentence)
                if current_embeddings is not None:
                    current_embeddings.append(sentence_embedding)
            else:
                # 保存当前块
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(chunk_text)
                
                # 开始新块
                current_chunk = [sentence]
                current_embeddings = [sentence_embedding] if sentence_embedding is not None else None
        
        # 添加最后一个块
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
        
        # 如果没有生成任何分块，至少返回一个包含所有内容的块
        if not chunks:
            logger.warning("语义分块未生成任何分块，返回完整文本")
            return [' '.join(sentences)]
        
        return chunks
    
    def _should_merge_sentence(self, current_chunk: List[str], new_sentence: str, 
                              current_embeddings: Optional[List], new_embedding: Optional) -> bool:
        """判断是否应该合并新句子到当前块"""
        # 长度检查
        current_text = ' '.join(current_chunk)
        if len(current_text) + len(new_sentence) > self.max_chunk_size:
            return False
        
        if len(current_chunk) >= self.semantic_config['max_chunk_sentences']:
            return False
        
        # 语义相似度检查
        if (self.semantic_config['use_embeddings'] and 
            current_embeddings is not None and 
            new_embedding is not None):
            semantic_similarity = self._calculate_semantic_similarity(current_embeddings, new_embedding)
        else:
            semantic_similarity = 0.0
        
        # 词汇相似度检查
        lexical_similarity = self._calculate_lexical_similarity(current_text, new_sentence)
        
        # 结构相似度检查
        structural_similarity = self._calculate_structural_similarity(current_text, new_sentence)
        
        # 综合相似度计算
        combined_similarity = (
            self.semantic_config['semantic_weight'] * semantic_similarity +
            self.semantic_config['lexical_weight'] * lexical_similarity +
            self.semantic_config['structural_weight'] * structural_similarity
        )
        
        # 自适应阈值
        threshold = self._get_adaptive_threshold(current_chunk, combined_similarity)
        
        return combined_similarity >= threshold
    
    def _calculate_semantic_similarity(self, current_embeddings: List, new_embedding) -> float:
        """计算语义相似度"""
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            # 计算当前块的平均嵌入
            current_avg = np.mean(current_embeddings, axis=0)
            
            # 计算余弦相似度
            similarity = cosine_similarity(
                current_avg.reshape(1, -1), 
                new_embedding.reshape(1, -1)
            )[0][0]
            
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"计算语义相似度失败: {e}")
            return 0.0
    
    def _calculate_lexical_similarity(self, text1: str, text2: str) -> float:
        """计算词汇相似度"""
        words1 = set(re.findall(r'[\u4e00-\u9fff]+|\b[a-zA-Z]+\b', text1.lower()))
        words2 = set(re.findall(r'[\u4e00-\u9fff]+|\b[a-zA-Z]+\b', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_structural_similarity(self, text1: str, text2: str) -> float:
        """计算结构相似度"""
        # 句子长度相似度
        len_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2), 1)
        
        # 标点符号相似度
        punct1 = set(re.findall(r'[^\w\s\u4e00-\u9fff]', text1))
        punct2 = set(re.findall(r'[^\w\s\u4e00-\u9fff]', text2))
        punct_similarity = len(punct1.intersection(punct2)) / max(len(punct1.union(punct2)), 1)
        
        return 0.6 * len_ratio + 0.4 * punct_similarity
    
    def _get_adaptive_threshold(self, current_chunk: List[str], current_similarity: float) -> float:
        """获取自适应阈值"""
        if not self.semantic_config['adaptive_threshold']:
            return self.semantic_config['similarity_threshold']
        
        # 基于当前块大小调整阈值
        chunk_size = len(current_chunk)
        base_threshold = self.semantic_config['similarity_threshold']
        
        # 块越大，阈值越高
        size_factor = min(chunk_size / 5.0, 1.0)
        adaptive_threshold = base_threshold + (0.2 * size_factor)
        
        return max(0.3, min(0.9, adaptive_threshold))
