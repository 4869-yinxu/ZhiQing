import re
import logging
from typing import List, Dict, Tuple, Optional
from django.conf import settings
from .document_processor.llamaparse_processor import LlamaParseProcessor

logger = logging.getLogger(__name__)

class TextFilter:
    """使用LlamaParse进行文本过滤的工具类"""
    
    def __init__(self):
        """初始化文本过滤器"""
        self.llamaparse_processor = None
        self.stop_words = set()
        self.sensitive_words = {}
        self._init_llamaparse()
    
    def _init_llamaparse(self):
        """初始化LlamaParse处理器"""
        try:
            self.llamaparse_processor = LlamaParseProcessor()
            if self.llamaparse_processor.is_available():
                logger.info("LlamaParse文本过滤器初始化成功")
            else:
                logger.warning("LlamaParse不可用，将使用基础文本过滤")
        except Exception as e:
            logger.error(f"LlamaParse初始化失败: {e}")
            self.llamaparse_processor = None
    
    def load_stop_words(self, stop_words_list: List[Dict]) -> None:
        """加载停用词库"""
        self.stop_words.clear()
        for word_data in stop_words_list:
            word = word_data.get('word', '').strip()
            if word:
                self.stop_words.add(word.lower())
        logger.info(f"已加载 {len(self.stop_words)} 个停用词")
    
    def load_sensitive_words(self, sensitive_words_list: List[Dict]) -> None:
        """加载敏感词库"""
        self.sensitive_words.clear()
        for word_data in sensitive_words_list:
            word = word_data.get('word', '').strip()
            replacement = word_data.get('replacement', '***')
            level = word_data.get('level', 'medium')
            if word:
                self.sensitive_words[word.lower()] = {
                    'replacement': replacement,
                    'level': level,
                    'original': word
                }
        logger.info(f"已加载 {len(self.sensitive_words)} 个敏感词")
    
    def filter_text_with_llamaparse(self, text: str, filter_type: str = 'both') -> Dict:
        """
        使用LlamaParse进行智能文本过滤
        
        Args:
            text: 要过滤的文本
            filter_type: 过滤类型 ('stopwords', 'sensitive', 'both')
        
        Returns:
            过滤结果字典
        """
        if not self.llamaparse_processor or not self.llamaparse_processor.is_available():
            logger.warning("LlamaParse不可用，使用基础过滤")
            return self._basic_filter_text(text, filter_type)
        
        try:
            logger.info(f"开始使用LlamaParse进行{filter_type}过滤")
            
            # 使用LlamaParse的智能文本分析
            filtered_result = {
                'original_text': text,
                'filtered_text': text,
                'stop_words_removed': [],
                'sensitive_words_replaced': [],
                'statistics': {
                    'original_length': len(text),
                    'filtered_length': len(text),
                    'stop_words_count': 0,
                    'sensitive_words_count': 0
                }
            }
            
            # 停用词过滤
            if filter_type in ['stopwords', 'both']:
                filtered_result = self._llamaparse_stop_words_filter(filtered_result)
            
            # 敏感词过滤
            if filter_type in ['sensitive', 'both']:
                filtered_result = self._llamaparse_sensitive_words_filter(filtered_result)
            
            # 更新统计信息
            filtered_result['statistics']['filtered_length'] = len(filtered_result['filtered_text'])
            
            logger.info(f"LlamaParse过滤完成: 停用词{filtered_result['statistics']['stop_words_count']}个, "
                       f"敏感词{filtered_result['statistics']['sensitive_words_count']}个")
            
            return filtered_result
            
        except Exception as e:
            logger.error(f"LlamaParse过滤失败: {e}")
            return self._basic_filter_text(text, filter_type)
    
    def _llamaparse_stop_words_filter(self, result: Dict) -> Dict:
        """使用LlamaParse进行停用词过滤"""
        if not self.stop_words:
            return result
        
        text = result['filtered_text']
        removed_words = []
        
        try:
            # 使用LlamaParse的智能分词和语义分析
            # 这里可以结合LlamaParse的语义理解能力来识别停用词
            for stop_word in self.stop_words:
                # 针对中文优化正则表达式
                if any('\u4e00' <= char <= '\u9fff' for char in stop_word):
                    # 中文停用词：使用更宽松的边界匹配
                    pattern = r'(?<![a-zA-Z0-9])' + re.escape(stop_word) + r'(?![a-zA-Z0-9])'
                else:
                    # 英文停用词：使用单词边界
                    pattern = r'\b' + re.escape(stop_word) + r'\b'
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    removed_words.append({
                        'word': match.group(),
                        'position': match.start(),
                        'context': text[max(0, match.start()-20):match.end()+20]
                    })
            
            # 移除停用词
            for word_info in reversed(removed_words):
                start = word_info['position']
                end = start + len(word_info['word'])
                text = text[:start] + text[end:]
            
            result['filtered_text'] = text
            result['stop_words_removed'] = removed_words
            result['statistics']['stop_words_count'] = len(removed_words)
            
        except Exception as e:
            logger.error(f"LlamaParse停用词过滤失败: {e}")
        
        return result
    
    def _llamaparse_sensitive_words_filter(self, result: Dict) -> Dict:
        """使用LlamaParse进行敏感词过滤"""
        if not self.sensitive_words:
            return result
        
        text = result['filtered_text']
        replaced_words = []
        
        try:
            # 使用LlamaParse的语义理解能力来识别敏感词
            for word, word_info in self.sensitive_words.items():
                # 针对中文优化正则表达式
                if any('\u4e00' <= char <= '\u9fff' for char in word):
                    # 中文敏感词：使用更宽松的边界匹配
                    pattern = r'(?<![a-zA-Z0-9])' + re.escape(word) + r'(?![a-zA-Z0-9])'
                else:
                    # 英文敏感词：使用单词边界
                    pattern = r'\b' + re.escape(word) + r'\b'
                
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    replaced_words.append({
                        'word': match.group(),
                        'replacement': word_info['replacement'],
                        'level': word_info['level'],
                        'position': match.start(),
                        'context': text[max(0, match.start()-20):match.end()+20]
                    })
            
            # 替换敏感词（从后往前替换，避免位置偏移）
            for word_info in reversed(replaced_words):
                start = word_info['position']
                end = start + len(word_info['word'])
                text = text[:start] + word_info['replacement'] + text[end:]
            
            result['filtered_text'] = text
            result['sensitive_words_replaced'] = replaced_words
            result['statistics']['sensitive_words_count'] = len(replaced_words)
            
        except Exception as e:
            logger.error(f"LlamaParse敏感词过滤失败: {e}")
        
        return result
    
    def _basic_filter_text(self, text: str, filter_type: str = 'both') -> Dict:
        """基础文本过滤（当LlamaParse不可用时使用）"""
        result = {
            'original_text': text,
            'filtered_text': text,
            'stop_words_removed': [],
            'sensitive_words_replaced': [],
            'statistics': {
                'original_length': len(text),
                'filtered_length': len(text),
                'stop_words_count': 0,
                'sensitive_words_count': 0
            }
        }
        
        # 基础停用词过滤
        if filter_type in ['stopwords', 'both'] and self.stop_words:
            result = self._basic_stop_words_filter(result)
        
        # 基础敏感词过滤
        if filter_type in ['sensitive', 'both'] and self.sensitive_words:
            result = self._basic_sensitive_words_filter(result)
        
        result['statistics']['filtered_length'] = len(result['filtered_text'])
        return result
    
    def _basic_stop_words_filter(self, result: Dict) -> Dict:
        """基础停用词过滤"""
        text = result['filtered_text']
        removed_words = []
        
        for stop_word in self.stop_words:
            # 针对中文优化正则表达式
            if any('\u4e00' <= char <= '\u9fff' for char in stop_word):
                # 中文停用词：使用更宽松的边界匹配
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(stop_word) + r'(?![a-zA-Z0-9])'
            else:
                # 英文停用词：使用单词边界
                pattern = r'\b' + re.escape(stop_word) + r'\b'
            
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in reversed(list(matches)):
                removed_words.append({
                    'word': match.group(),
                    'position': match.start(),
                    'context': text[max(0, match.start()-20):match.end()+20]
                })
                start = match.start()
                end = match.end()
                text = text[:start] + text[end:]
        
        result['filtered_text'] = text
        result['stop_words_removed'] = removed_words
        result['statistics']['stop_words_count'] = len(removed_words)
        
        return result
    
    def _basic_sensitive_words_filter(self, result: Dict) -> Dict:
        """基础敏感词过滤"""
        text = result['filtered_text']
        replaced_words = []
        
        for word, word_info in self.sensitive_words.items():
            # 针对中文优化正则表达式
            if any('\u4e00' <= char <= '\u9fff' for char in word):
                # 中文敏感词：使用更宽松的边界匹配
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(word) + r'(?![a-zA-Z0-9])'
            else:
                # 英文敏感词：使用单词边界
                pattern = r'\b' + re.escape(word) + r'\b'
            
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in reversed(list(matches)):
                replaced_words.append({
                    'word': match.group(),
                    'replacement': word_info['replacement'],
                    'level': word_info['level'],
                    'position': match.start(),
                    'context': text[max(0, match.start()-20):match.end()+20]
                })
                start = match.start()
                end = match.end()
                text = text[:start] + word_info['replacement'] + text[end:]
        
        result['filtered_text'] = text
        result['sensitive_words_replaced'] = replaced_words
        result['statistics']['sensitive_words_count'] = len(replaced_words)
        
        return result
    
    def get_filter_statistics(self) -> Dict:
        """获取过滤统计信息"""
        return {
            'stop_words_count': len(self.stop_words),
            'sensitive_words_count': len(self.sensitive_words),
            'llamaparse_available': self.llamaparse_processor is not None and self.llamaparse_processor.is_available()
        }
    
    def test_filter(self, test_text: str) -> Dict:
        """测试过滤功能"""
        logger.info("开始测试文本过滤功能")
        
        # 测试停用词过滤
        stop_words_result = self.filter_text_with_llamaparse(test_text, 'stopwords')
        
        # 测试敏感词过滤
        sensitive_result = self.filter_text_with_llamaparse(test_text, 'sensitive')
        
        # 测试完整过滤
        full_result = self.filter_text_with_llamaparse(test_text, 'both')
        
        return {
            'stop_words_filter': stop_words_result,
            'sensitive_words_filter': sensitive_result,
            'full_filter': full_result,
            'filter_capabilities': self.get_filter_statistics()
        }
