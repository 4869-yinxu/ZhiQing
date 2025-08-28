"""
兼容原有txt处理的文档处理器
保持向后兼容性
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from .base_processor import BaseDocumentProcessor

logger = logging.getLogger(__name__)


class LegacyDocumentProcessor(BaseDocumentProcessor):
    """兼容原有txt处理的文档处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})
        
        # 支持多种格式
        self.supported_formats = ['.txt', '.pdf', '.docx', '.doc', '.md', '.markdown']
        
        # 继承原有配置
        self.chunking_method = self.config.get('chunking_method', 'token')
        self.chunk_size = self.config.get('chunk_size', 500)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        self.overlap_size = self.config.get('overlap_size', 100)
        self.custom_delimiter = self.config.get('custom_delimiter', '\n\n')
        self.window_size = self.config.get('window_size', 3)
        self.step_size = self.config.get('step_size', 1)
        self.min_chunk_size = self.config.get('min_chunk_size', 50)
        self.max_chunk_size = self.config.get('max_chunk_size', 2000)
        
    def is_available(self) -> bool:
        """检查处理器是否可用"""
        return True  # Legacy处理器总是可用的
    
    def can_process(self, file_path: str) -> bool:
        """检查是否可以处理指定文件"""
        if not self.validate_file(file_path):
            return False
            
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_formats
    
    def extract_text(self, file_path: str) -> str:
        """从文件中提取文本内容"""
        try:
            self.log_processing(file_path, "开始提取文本")
            
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"读取文本文件: {file_path}, 长度: {len(content)}")
                    logger.debug(f"文件内容: {content[:100]}...")
            elif file_ext == '.pdf':
                content = self._extract_pdf_text(file_path)
            elif file_ext in ['.docx', '.doc']:
                content = self._extract_docx_text(file_path)
            elif file_ext in ['.md', '.markdown']:
                content = self._extract_markdown_text(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            self.log_processing(file_path, "文本提取完成")
            return content
            
        except Exception as e:
            self.handle_error(file_path, e, "文本提取")
    
    def extract_structure(self, file_path: str) -> Dict[str, Any]:
        """提取文档结构信息"""
        try:
            self.log_processing(file_path, "开始提取文档结构")
            
            file_ext = Path(file_path).suffix.lower()
            content = self.extract_text(file_path)
            lines = content.split('\n')
            
            # 简单的段落识别
            paragraphs = []
            current_paragraph = []
            
            for line in lines:
                line = line.strip()
                if line:
                    current_paragraph.append(line)
                elif current_paragraph:
                    paragraphs.append('\n'.join(current_paragraph))
                    current_paragraph = []
            
            # 添加最后一个段落
            if current_paragraph:
                paragraphs.append('\n'.join(current_paragraph))
            
            structure_info = {
                'file_path': file_path,
                'file_type': file_ext,
                'processor': self.processor_name,
                'headings': [],  # 简单结构，没有标题识别
                'sections': [{'type': 'paragraph', 'text': p} for p in paragraphs],
                'paragraph_count': len(paragraphs),
                'line_count': len(lines)
            }
            
            self.log_processing(file_path, "文档结构提取完成")
            return structure_info
            
        except Exception as e:
            self.handle_error(file_path, e, "文档结构提取")
    
    def split_text(self, text: str) -> List[str]:
        """根据指定方法分割文本（保持原有逻辑）"""
        chunks = []

        if self.chunking_method == "token":
            chunks = self._split_by_token(text)
        elif self.chunking_method == "sentence":
            chunks = self._split_by_sentence(text)
        elif self.chunking_method == "paragraph":
            chunks = self._split_by_paragraph(text)
        elif self.chunking_method == "chapter":
            chunks = self._split_by_chapter(text)
        elif self.chunking_method == "semantic":
            chunks = self._split_by_semantic(text)
        elif self.chunking_method == "recursive":
            chunks = self._split_recursive(text)
        elif self.chunking_method == "sliding_window":
            chunks = self._split_by_sliding_window(text)
        elif self.chunking_method == "custom_delimiter":
            chunks = self._split_by_custom_delimiter(text)
        elif self.chunking_method == "fixed_length":
            chunks = self._split_by_fixed_length(text)
        else:
            logger.warning(f"未实现的分块方法: {self.chunking_method}，使用Token分块")
            chunks = self._split_by_token(text)

        # 过滤空块和过小的块
        chunks = [chunk.strip() for chunk in chunks if chunk.strip() and len(chunk.strip()) >= self.min_chunk_size]
        
        # 对于自定义分隔符分块，不进行自动合并，保持用户指定的分割结果
        if self.chunking_method != "custom_delimiter":
            # 合并过小的块
            chunks = self._merge_small_chunks(chunks)
        
        logger.info(f"使用 {self.chunking_method} 方法分割文本，生成 {len(chunks)} 个分块")
        return chunks
    
    def _split_by_token(self, text: str) -> List[str]:
        """按Token数量分块"""
        # 简单的Token估算（按字符数）
        estimated_tokens = len(text) // 4  # 假设1个token约等于4个字符
        
        logger.info(f"Token分块: 文本长度={len(text)}, 估算token数={estimated_tokens}, chunk_size={self.chunk_size}")
        
        if estimated_tokens <= self.chunk_size:
            logger.info(f"文本长度小于等于chunk_size，返回整个文本")
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            end_pos = min(current_pos + self.chunk_size * 4, len(text))
            
            # 尝试在合适的位置断开
            if end_pos < len(text):
                # 寻找句号、换行等自然断点
                for i in range(min(100, end_pos - current_pos)):
                    if text[end_pos - i] in ['.', '!', '?', '\n', '。', '！', '？', '；', ';']:
                        end_pos = end_pos - i + 1
                        break
            
            chunk = text[current_pos:end_pos]
            if chunk.strip():
                chunks.append(chunk)
            
            current_pos = end_pos
            
        return chunks
    
    def _split_by_sentence(self, text: str) -> List[str]:
        """按句子分块"""
        import re
        
        # 简单的句子分割
        sentences = re.split(r'[.!?。！？]+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _split_by_paragraph(self, text: str) -> List[str]:
        """按段落分块"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            paragraph_length = len(paragraph)
            
            if current_length + paragraph_length > self.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_length = paragraph_length
            else:
                current_chunk.append(paragraph)
                current_length += paragraph_length
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _split_by_chapter(self, text: str) -> List[str]:
        """按章节分块（基于Markdown标题层级）"""
        import re
        
        # 查找Markdown标题（支持 # ## ### 等格式）
        # 同时支持数字标题格式（如 1. 2. 等）
        chapter_patterns = [
            r'^(#{1,6})\s+([^\n]+)',  # Markdown标题: # ## ###
            r'^(\d+\.?\s*[^\n]+)',    # 数字标题: 1. 2. 等
        ]
        
        chapters = []
        for pattern in chapter_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            if matches:
                if pattern == r'^(#{1,6})\s+([^\n]+)':
                    # Markdown标题格式
                    for level, title in matches:
                        chapters.append((len(level), title, text.find(f"{level} {title}")))
                else:
                    # 数字标题格式
                    for title in matches:
                        chapters.append((1, title, text.find(title)))
                break
        
        if not chapters:
            # 如果没有找到章节，按段落分块
            return self._split_by_paragraph(text)
        
        # 按位置排序
        chapters.sort(key=lambda x: x[2])
        
        chunks = []
        current_chunk = ""
        current_length = 0
        
        for i, (level, chapter_title, start_pos) in enumerate(chapters):
            if i < len(chapters) - 1:
                next_chapter_pos = chapters[i + 1][2]
                end_pos = next_chapter_pos
            else:
                end_pos = len(text)
            
            chapter_content = text[start_pos:end_pos].strip()
            if chapter_content:
                # 如果当前分块太小，尝试合并
                if len(chapter_content) < self.min_chunk_size:
                    if current_chunk:
                        # 添加到累积块
                        current_chunk += "\n\n" + chapter_content
                        current_length += len(chapter_content)
                    else:
                        # 开始新的累积块
                        current_chunk = chapter_content
                        current_length = len(chapter_content)
                else:
                    # 当前分块足够大，处理累积块
                    if current_chunk:
                        # 尝试合并累积块和当前分块
                        if current_length + len(chapter_content) <= self.max_chunk_size:
                            # 合并成功
                            current_chunk += "\n\n" + chapter_content
                            chunks.append(current_chunk)
                        else:
                            # 合并失败，分别添加
                            chunks.append(current_chunk)
                            chunks.append(chapter_content)
                        current_chunk = ""
                        current_length = 0
                    else:
                        # 没有累积块，直接处理当前分块
                        if len(chapter_content) > self.max_chunk_size:
                            # 分块太大，进一步分割
                            sub_chunks = self._split_large_chapter(chapter_content)
                            chunks.extend(sub_chunks)
                        else:
                            chunks.append(chapter_content)
        
        # 处理最后的累积块
        if current_chunk:
            # 尝试与最后一个分块合并
            if chunks and len(chunks[-1]) + len(current_chunk) <= self.max_chunk_size:
                chunks[-1] += "\n\n" + current_chunk
            else:
                chunks.append(current_chunk)
        
        # 后处理：合并过小的相邻分块
        final_chunks = []
        i = 0
        while i < len(chunks):
            current_chunk = chunks[i]
            current_length = len(current_chunk)
            
            # 如果当前分块太小，尝试与下一个分块合并
            if current_length < self.min_chunk_size and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                combined_length = current_length + len(next_chunk)
                
                if combined_length <= self.max_chunk_size:
                    # 合并分块
                    final_chunks.append(current_chunk + "\n\n" + next_chunk)
                    i += 2  # 跳过下一个分块
                else:
                    final_chunks.append(current_chunk)
                    i += 1
            else:
                final_chunks.append(current_chunk)
                i += 1
        
        return final_chunks
    
    def _split_large_chapter(self, chapter_content: str) -> List[str]:
        """分割过大的章节内容"""
        chunks = []
        lines = chapter_content.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line)
            
            # 如果当前行是标题，且当前块不为空，先保存当前块
            if line.strip().startswith('#') and current_chunk:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            # 如果添加当前行会超过最大分块大小，保存当前块并开始新块
            elif current_length + line_length > self.max_chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length
        
        # 添加最后一个块
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _split_by_semantic(self, text: str) -> List[str]:
        """基于语义的分块"""
        # 简化的语义分块（基于词汇相似度）
        sentences = text.split('.')
        chunks = []
        current_chunk = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk) > 0:
                # 计算与当前块的相似度
                similarity = self._calculate_similarity(current_chunk[-1], sentence)
                
                if similarity > self.similarity_threshold and len(' '.join(current_chunk)) < self.max_chunk_size:
                    current_chunk.append(sentence)
                else:
                    if current_chunk:
                        chunks.append('. '.join(current_chunk))
                    current_chunk = [sentence]
            else:
                current_chunk.append(sentence)
        
        if current_chunk:
            chunks.append('. '.join(current_chunk))
        
        return chunks
    
    def _split_recursive(self, text: str) -> List[str]:
        """递归分块（带重叠）"""
        chunks = []
        total_length = len(text)
        start = 0
        
        while start < total_length:
            end = min(start + self.chunk_size, total_length)
            
            # 尝试在合适的位置断开
            if end < total_length:
                for i in range(min(100, end - start)):
                    if text[end - i] in ['.', '!', '?', '\n', '。', '！', '？', '；', ';']:
                        end = end - i + 1
                        break
            
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            
            # 计算下一个起始位置（考虑重叠）
            if end < total_length:
                start = max(start + 1, end - self.overlap_size)
            else:
                break
                
        return chunks
    
    def _split_by_sliding_window(self, text: str) -> List[str]:
        """滑动窗口分块"""
        chunks = []
        total_length = len(text)
        
        for start in range(0, total_length, self.step_size):
            end = min(start + self.window_size * self.chunk_size, total_length)
            
            if end - start >= self.min_chunk_size:
                chunk = text[start:end]
                if chunk.strip():
                    chunks.append(chunk)
        
        return chunks
    
    def _split_by_custom_delimiter(self, text: str) -> List[str]:
        """按自定义分隔符分块"""
        if not self.custom_delimiter:
            return [text]
        
        chunks = text.split(self.custom_delimiter)
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    
    def _split_by_fixed_length(self, text: str) -> List[str]:
        """按固定长度分块"""
        chunks = []
        total_length = len(text)
        
        for start in range(0, total_length, self.chunk_size):
            end = min(start + self.chunk_size, total_length)
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        import re
        
        # 词汇相似度
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """合并过小的块"""
        if not chunks:
            return chunks
        
        merged_chunks = []
        current_chunk = chunks[0]
        
        for i in range(1, len(chunks)):
            next_chunk = chunks[i]
            
            # 如果当前块太小，尝试合并下一个块
            if len(current_chunk) < self.min_chunk_size:
                combined = current_chunk + '\n\n' + next_chunk
                if len(combined) <= self.max_chunk_size:
                    current_chunk = combined
                else:
                    merged_chunks.append(current_chunk)
                    current_chunk = next_chunk
            else:
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk
        
        merged_chunks.append(current_chunk)
        return merged_chunks
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """从PDF文件中提取文本"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            raise ImportError("PyMuPDF未安装，无法处理PDF文件")
        except Exception as e:
            raise Exception(f"PDF文本提取失败: {e}")
    
    def _extract_docx_text(self, file_path: str) -> str:
        """从DOCX文件中提取文本"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            raise ImportError("python-docx未安装，无法处理DOCX文件")
        except Exception as e:
            raise Exception(f"DOCX文本提取失败: {e}")
    
    def _extract_markdown_text(self, file_path: str) -> str:
        """从Markdown文件中提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            raise Exception(f"Markdown文本提取失败: {e}")
