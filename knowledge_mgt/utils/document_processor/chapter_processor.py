#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
章节分块处理器
专门处理基于标题层级的文档分块
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from .legacy_processor import LegacyDocumentProcessor
from .chapter_config import ChapterConfig, create_config_for_document_type, create_config_for_language

logger = logging.getLogger(__name__)


class ChapterProcessor(LegacyDocumentProcessor):
    """专门的章节分块处理器"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config or {})
        self.chapter_config = ChapterConfig(config)
        self.title_patterns = self._init_title_patterns()
        self.hierarchy_detection = self.chapter_config.is_feature_enabled('hierarchy_detection')
        self.merge_small_chapters = self.chapter_config.is_feature_enabled('merge_small_chapters')
        self.max_chapter_size = self.chapter_config.get_config('max_chapter_size')
        
    def _init_title_patterns(self) -> List[Dict]:
        """初始化标题识别模式"""
        return [
            # Markdown标题 (支持1-6级)
            {
                'pattern': r'^(#{1,6})\s+(.+)$',
                'type': 'markdown',
                'level_extractor': lambda m: len(m.group(1)),
                'title_extractor': lambda m: m.group(2).strip(),
                'priority': 1
            },
            # 中文章节标题
            {
                'pattern': r'^第([一二三四五六七八九十\d]+)[章节部分]\s*(.+)$',
                'type': 'chinese_chapter',
                'level_extractor': lambda m: self._chinese_to_number(m.group(1)),
                'title_extractor': lambda m: m.group(2).strip(),
                'priority': 2
            },
            # 中文小节标题
            {
                'pattern': r'^([一二三四五六七八九十\d]+)\.\s*(.+)$',
                'type': 'chinese_section',
                'level_extractor': lambda m: self._chinese_to_number(m.group(1)) + 10,
                'title_extractor': lambda m: m.group(2).strip(),
                'priority': 3
            },
            # 英文章节标题
            {
                'pattern': r'^Chapter\s+(\d+)(?:\s*[-:]\s*(.+))?$',
                'type': 'english_chapter',
                'level_extractor': lambda m: int(m.group(1)),
                'title_extractor': lambda m: m.group(2).strip() if m.group(2) else f"Chapter {m.group(1)}",
                'priority': 4
            },
            # 英文小节标题
            {
                'pattern': r'^(\d+)\.(\d+)(?:\s*[-:]\s*(.+))?$',
                'type': 'english_section',
                'level_extractor': lambda m: int(m.group(1)) * 100 + int(m.group(2)),
                'title_extractor': lambda m: m.group(3).strip() if m.group(3) else f"{m.group(1)}.{m.group(2)}",
                'priority': 5
            },
            # 数字标题 (1. 2. 3.)
            {
                'pattern': r'^(\d+)\.\s*(.+)$',
                'type': 'numeric',
                'level_extractor': lambda m: int(m.group(1)),
                'title_extractor': lambda m: m.group(2).strip(),
                'priority': 6
            },
            # 字母标题 (A. B. C.)
            {
                'pattern': r'^([A-Z])\.\s*(.+)$',
                'type': 'alphabetic',
                'level_extractor': lambda m: ord(m.group(1)) - ord('A') + 1,
                'title_extractor': lambda m: m.group(2).strip(),
                'priority': 7
            },
            # 全大写标题
            {
                'pattern': r'^([A-Z][A-Z\s]{2,})$',
                'type': 'uppercase',
                'level_extractor': lambda m: 1,
                'title_extractor': lambda m: m.group(1).strip(),
                'priority': 8
            },
            # 中文大写标题
            {
                'pattern': r'^([一二三四五六七八九十]+)\s*(.+)$',
                'type': 'chinese_uppercase',
                'level_extractor': lambda m: self._chinese_to_number(m.group(1)),
                'title_extractor': lambda m: m.group(2).strip(),
                'priority': 9
            }
        ]
    
    def _chinese_to_number(self, chinese: str) -> int:
        """将中文数字转换为阿拉伯数字"""
        chinese_nums = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }
        
        if chinese.isdigit():
            return int(chinese)
        
        result = 0
        for char in chinese:
            if char in chinese_nums:
                result = result * 10 + chinese_nums[char]
        return result if result > 0 else 1
    
    def split_text(self, text: str) -> List[str]:
        """章节分块主方法"""
        logger.info("开始章节分块处理")
        
        # 1. 提取标题结构
        title_structure = self._extract_title_structure(text)
        
        if not title_structure:
            logger.info("未检测到标题结构，回退到段落分块")
            return self._split_by_paragraph(text)
        
        # 2. 按标题分块
        chunks = self._split_by_title_structure(text, title_structure)
        
        # 3. 后处理：合并过小的块
        if self.merge_small_chapters:
            chunks = self._merge_small_chunks(chunks)
        
        # 4. 验证分块质量
        chunks = self._validate_chunks(chunks)
        
        logger.info(f"章节分块完成，共生成 {len(chunks)} 个分块")
        return chunks
    
    def _extract_title_structure(self, text: str) -> List[Dict]:
        """提取文档的标题结构"""
        lines = text.split('\n')
        titles = []
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 检查所有标题模式
            for pattern_info in self.title_patterns:
                match = re.match(pattern_info['pattern'], line, re.IGNORECASE)
                if match:
                    title_info = {
                        'line_number': line_num,
                        'line_content': line,
                        'type': pattern_info['type'],
                        'level': pattern_info['level_extractor'](match),
                        'title': pattern_info['title_extractor'](match),
                        'priority': pattern_info['priority'],
                        'start_pos': text.find(line, sum(len(l) + 1 for l in lines[:line_num]))
                    }
                    titles.append(title_info)
                    break  # 一个标题只匹配一个模式
        
        # 按优先级和位置排序
        titles.sort(key=lambda x: (x['priority'], x['line_number']))
        
        logger.info(f"检测到 {len(titles)} 个标题")
        for title in titles:
            logger.debug(f"标题: {title['title']} (级别: {title['level']}, 类型: {title['type']})")
        
        return titles
    
    def _split_by_title_structure(self, text: str, title_structure: List[Dict]) -> List[str]:
        """根据标题结构进行分块"""
        if not title_structure:
            return [text]
        
        chunks = []
        lines = text.split('\n')
        
        for i, title_info in enumerate(title_structure):
            start_line = title_info['line_number']
            
            # 确定结束位置
            if i < len(title_structure) - 1:
                end_line = title_structure[i + 1]['line_number']
            else:
                end_line = len(lines)
            
            # 提取章节内容
            chapter_lines = lines[start_line:end_line]
            chapter_text = '\n'.join(chapter_lines).strip()
            
            # 如果章节太小，尝试合并到下一个章节
            if len(chapter_text) < self.min_chunk_size:
                logger.debug(f"章节 '{title_info['title']}' 太小 ({len(chapter_text)} < {self.min_chunk_size})，尝试合并")
                # 不跳过，而是添加到当前块中
                if chunks:
                    # 合并到前一个块
                    chunks[-1] += "\n\n" + chapter_text
                else:
                    # 第一个块，直接添加
                    chunks.append(chapter_text)
            else:
                # 如果章节太大，进一步分割
                if len(chapter_text) > self.max_chapter_size:
                    sub_chunks = self._split_large_chapter(chapter_text, title_info)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chapter_text)
        
        return chunks
    
    def _split_large_chapter(self, chapter_text: str, title_info: Dict) -> List[str]:
        """分割过大的章节"""
        logger.debug(f"分割过大章节: {title_info['title']} (长度: {len(chapter_text)})")
        
        # 尝试按段落分割
        paragraphs = chapter_text.split('\n\n')
        if len(paragraphs) > 1:
            chunks = []
            current_chunk = []
            current_length = 0
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                if current_length + len(para) > self.max_chapter_size and current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [para]
                    current_length = len(para)
                else:
                    current_chunk.append(para)
                    current_length += len(para)
            
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            
            return chunks
        
        # 如果段落分割效果不好，按句子分割
        return self._split_by_sentence(chapter_text)
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """合并过小的分块"""
        if not chunks:
            return chunks
        
        merged_chunks = []
        current_chunk = ""
        
        for chunk in chunks:
            if len(current_chunk) + len(chunk) <= self.max_chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + chunk
                else:
                    current_chunk = chunk
            else:
                if current_chunk:
                    merged_chunks.append(current_chunk)
                current_chunk = chunk
        
        if current_chunk:
            merged_chunks.append(current_chunk)
        
        logger.info(f"合并后分块数量: {len(chunks)} -> {len(merged_chunks)}")
        return merged_chunks
    
    def _validate_chunks(self, chunks: List[str]) -> List[str]:
        """验证分块质量"""
        valid_chunks = []
        
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if not chunk:
                continue
            
            # 检查最小长度
            if len(chunk) < self.min_chunk_size:
                logger.warning(f"分块 {i+1} 过小 ({len(chunk)} < {self.min_chunk_size})，跳过")
                continue
            
            # 检查最大长度
            if len(chunk) > self.max_chunk_size:
                logger.warning(f"分块 {i+1} 过大 ({len(chunk)} > {self.max_chunk_size})，需要进一步分割")
                # 这里可以添加更智能的分割逻辑
                sub_chunks = self._split_by_sentence(chunk)
                valid_chunks.extend(sub_chunks)
            else:
                valid_chunks.append(chunk)
        
        return valid_chunks
    
    def get_chapter_summary(self, text: str) -> Dict:
        """获取章节摘要信息"""
        title_structure = self._extract_title_structure(text)
        
        summary = {
            'total_titles': len(title_structure),
            'title_types': {},
            'hierarchy_levels': set(),
            'chapters': []
        }
        
        for title in title_structure:
            # 统计标题类型
            title_type = title['type']
            summary['title_types'][title_type] = summary['title_types'].get(title_type, 0) + 1
            
            # 统计层级
            summary['hierarchy_levels'].add(title['level'])
            
            # 章节信息
            summary['chapters'].append({
                'title': title['title'],
                'level': title['level'],
                'type': title['type']
            })
        
        summary['hierarchy_levels'] = sorted(list(summary['hierarchy_levels']))
        
        return summary
