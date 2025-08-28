"""
基础文档处理器接口
定义所有文档处理器必须实现的方法
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseDocumentProcessor(ABC):
    """文档处理器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化处理器
        
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.supported_formats = []
        self.processor_name = self.__class__.__name__
        
    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """
        检查是否可以处理指定文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否可以处理
        """
        pass
    
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """
        从文件中提取文本内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 提取的文本内容
        """
        pass
    
    @abstractmethod
    def extract_structure(self, file_path: str) -> Dict[str, Any]:
        """
        提取文档结构信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文档结构信息
        """
        pass
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        return self.supported_formats
    
    def validate_file(self, file_path: str) -> bool:
        """
        验证文件是否有效
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否有效
        """
        path = Path(file_path)
        return path.exists() and path.is_file()
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件基本信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文件信息
        """
        path = Path(file_path)
        return {
            'name': path.name,
            'size': path.stat().st_size,
            'extension': path.suffix.lower(),
            'path': str(path.absolute())
        }
    
    def log_processing(self, file_path: str, operation: str, status: str = "success"):
        """记录处理日志"""
        logger.info(f"[{self.processor_name}] {operation} {file_path}: {status}")
    
    def handle_error(self, file_path: str, error: Exception, operation: str):
        """统一错误处理"""
        error_msg = f"[{self.processor_name}] {operation} {file_path} 失败: {str(error)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)
