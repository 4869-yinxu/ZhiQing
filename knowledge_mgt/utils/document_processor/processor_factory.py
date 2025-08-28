"""
文档处理器工厂
根据文件类型自动选择合适的处理器
"""

import logging
from typing import Dict, List, Any, Optional, Type
from pathlib import Path

from .base_processor import BaseDocumentProcessor
from .llamaindex_processor import LlamaIndexProcessor
from .legacy_processor import LegacyDocumentProcessor
from .llamaparse_processor import LlamaParseProcessor
from .chapter_processor import ChapterProcessor
from .semantic_processor import SemanticProcessor
from .excel_processor import ExcelProcessor

logger = logging.getLogger(__name__)


class DocumentProcessorFactory:
    """文档处理器工厂类"""
    
    def __init__(self):
        """初始化工厂"""
        self.processors: Dict[str, Type[BaseDocumentProcessor]] = {}
        self._register_processors()
    
    def _register_processors(self):
        """注册可用的处理器"""
        # 优先注册LlamaParse处理器（最新最强大）
        try:
            test_processor = LlamaParseProcessor()
            if test_processor.is_available():
                self.processors['llamaparse'] = LlamaParseProcessor
                logger.info("LlamaParse处理器注册成功")
            else:
                logger.warning("LlamaParse处理器不可用，跳过注册")
        except Exception as e:
            logger.warning(f"LlamaParse处理器不可用，跳过注册: {e}")
        
        # 检查LlamaIndex处理器是否真正可用
        try:
            # 尝试创建LlamaIndexProcessor实例来验证是否真正可用
            test_processor = LlamaIndexProcessor()
            self.processors['llamaindex'] = LlamaIndexProcessor
            logger.info("LlamaIndex处理器注册成功")
        except Exception as e:
            logger.warning(f"LlamaIndex处理器不可用，跳过注册: {e}")
        
        # 注册章节处理器（专门处理章节分块）
        try:
            test_processor = ChapterProcessor()
            self.processors['chapter'] = ChapterProcessor
            logger.info("章节处理器注册成功")
        except Exception as e:
            logger.warning(f"章节处理器不可用，跳过注册: {e}")
        
        # 注册语义处理器（专门处理语义分块）
        try:
            # 不创建实例，只注册类，避免预加载模型
            self.processors['semantic'] = SemanticProcessor
            logger.info("语义处理器注册成功（按需加载模型）")
        except Exception as e:
            logger.warning(f"语义处理器不可用，跳过注册: {e}")
        
        # 注册Excel处理器（专门处理Excel文件）
        try:
            test_processor = ExcelProcessor()
            self.processors['excel'] = ExcelProcessor
            logger.info("Excel处理器注册成功")
        except Exception as e:
            logger.warning(f"Excel处理器不可用，跳过注册: {e}")
        
        # 注册Legacy处理器（兼容原有功能）
        self.processors['legacy'] = LegacyDocumentProcessor
        logger.info("Legacy处理器注册成功")
    
    def get_processor(self, file_path: str, processor_type: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> BaseDocumentProcessor:
        """
        获取适合的文档处理器
        
        Args:
            file_path: 文件路径
            processor_type: 指定的处理器类型（可选）
            config: 处理器配置
            
        Returns:
            BaseDocumentProcessor: 文档处理器实例
            
        Raises:
            ValueError: 当没有合适的处理器时
        """
        # URL不要求本地存在
        if not str(file_path).lower().startswith(("http://", "https://")):
            if not Path(file_path).exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 如果指定了处理器类型
        if processor_type and processor_type in self.processors:
            try:
                processor_class = self.processors[processor_type]
                return processor_class(config or {})
            except Exception as e:
                logger.warning(f"使用指定处理器 {processor_type} 失败: {e}")
                # 回退到自动选择
        
        # 自动选择合适的处理器
        return self._auto_select_processor(file_path, config)
    
    def _auto_select_processor(self, file_path: str, config: Optional[Dict[str, Any]] = None) -> BaseDocumentProcessor:
        """
        自动选择合适的处理器
        
        Args:
            file_path: 文件路径
            config: 处理器配置
            
        Returns:
            BaseDocumentProcessor: 文档处理器实例
        """
        file_ext = Path(file_path).suffix.lower()
        
        # 特殊文件格式处理：Markdown文件优先使用Legacy处理器
        if file_ext in ['.md', '.markdown']:
            try:
                processor = LegacyDocumentProcessor(config or {})
                logger.info(f"Markdown文件使用Legacy处理器处理: {file_path}")
                return processor
            except Exception as e:
                logger.warning(f"Legacy处理器创建失败: {e}")
        
        # 优先尝试LlamaParse处理器（最新最强大）
        if 'llamaparse' in self.processors:
            try:
                processor = LlamaParseProcessor(config or {})
                if processor.can_process(file_path):
                    logger.info(f"自动选择LlamaParse处理器处理文件: {file_path}")
                    return processor
                else:
                    logger.debug(f"LlamaParse处理器无法处理文件: {file_path}")
            except Exception as e:
                logger.warning(f"LlamaParse处理器创建失败: {e}")
        
        # 尝试LlamaIndex处理器
        if 'llamaindex' in self.processors:
            try:
                processor = LlamaIndexProcessor(config or {})
                if processor.can_process(file_path):
                    logger.info(f"自动选择LlamaIndex处理器处理文件: {file_path}")
                    return processor
                else:
                    logger.debug(f"LlamaIndex处理器无法处理文件: {file_path}")
            except Exception as e:
                logger.warning(f"LlamaIndex处理器创建失败: {e}")
        
        # 最后使用Legacy处理器（兼容性最好）
        try:
            processor = LegacyDocumentProcessor(config or {})
            logger.info(f"使用Legacy处理器处理文件: {file_path}")
            return processor
        except Exception as e:
            logger.error(f"Legacy处理器创建失败: {e}")
            raise ValueError(f"没有可用的文档处理器来处理文件: {file_path}")
    
    def get_supported_formats(self) -> List[str]:
        """获取所有处理器支持的文件格式"""
        all_formats = set()
        
        for proc_type, proc_class in self.processors.items():
            try:
                proc = proc_class()
                all_formats.update(proc.get_supported_formats())
            except Exception as e:
                logger.warning(f"获取处理器 {proc_type} 支持格式失败: {e}")
        
        return sorted(list(all_formats))
    
    def get_processor_info(self) -> Dict[str, Any]:
        """获取所有处理器的信息"""
        processor_info = {}
        
        for proc_type, proc_class in self.processors.items():
            try:
                proc = proc_class()
                processor_info[proc_type] = {
                    'name': proc.processor_name,
                    'supported_formats': proc.get_supported_formats(),
                    'available': True
                }
            except Exception as e:
                processor_info[proc_type] = {
                    'name': proc_class.__name__,
                    'supported_formats': [],
                    'available': False,
                    'error': str(e)
                }
        
        return processor_info
    
    def test_processor(self, processor_type: str, test_file: str) -> Dict[str, Any]:
        """
        测试指定处理器的功能
        
        Args:
            processor_type: 处理器类型
            test_file: 测试文件路径
            
        Returns:
            Dict: 测试结果
        """
        if processor_type not in self.processors:
            return {
                'success': False,
                'error': f'处理器类型 {processor_type} 不存在'
            }
        
        try:
            processor = self.processors[processor_type]()
            
            # 测试文件处理能力
            can_process = processor.can_process(test_file)
            if not can_process:
                return {
                    'success': False,
                    'error': f'处理器无法处理文件 {test_file}'
                }
            
            # 测试文本提取
            text = processor.extract_text(test_file)
            text_length = len(text) if text else 0
            
            # 测试结构提取
            structure = processor.extract_structure(test_file)
            
            return {
                'success': True,
                'processor_type': processor_type,
                'file': test_file,
                'text_length': text_length,
                'structure': structure,
                'supported_formats': processor.get_supported_formats()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processor_type': processor_type,
                'file': test_file
            }


# 全局工厂实例
document_processor_factory = DocumentProcessorFactory()


def get_document_processor(file_path: str, processor_type: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> BaseDocumentProcessor:
    """
    便捷函数：获取文档处理器
    
    Args:
        file_path: 文件路径
        processor_type: 处理器类型（可选）
        config: 处理器配置（可选）
        
    Returns:
        BaseDocumentProcessor: 文档处理器实例
    """
    return document_processor_factory.get_processor(file_path, processor_type, config)


def get_supported_formats() -> List[str]:
    """便捷函数：获取支持的文件格式"""
    return document_processor_factory.get_supported_formats()


def get_processor_info() -> Dict[str, Any]:
    """便捷函数：获取处理器信息"""
    return document_processor_factory.get_processor_info()
