#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
章节分块配置
定义章节分块的各种参数和选项
"""

from typing import Dict, List, Any

# 默认配置
DEFAULT_CHAPTER_CONFIG = {
    # 分块大小控制
    'min_chunk_size': 50,           # 最小分块大小（字符数）
    'max_chunk_size': 2000,         # 最大分块大小（字符数）
    'max_chapter_size': 5000,       # 最大章节大小（字符数）
    'chunk_size': 1000,             # 目标分块大小（字符数）
    
    # 标题识别配置
    'hierarchy_detection': True,     # 是否启用层级检测
    'merge_small_chapters': True,    # 是否合并过小的章节
    'smart_title_detection': True,   # 是否启用智能标题检测
    
    # 标题模式优先级
    'title_pattern_priorities': {
        'markdown': 1,               # Markdown标题优先级最高
        'chinese_chapter': 2,        # 中文章节标题
        'chinese_section': 3,        # 中文小节标题
        'english_chapter': 4,        # 英文章节标题
        'english_section': 5,        # 英文小节标题
        'numeric': 6,                # 数字标题
        'alphabetic': 7,             # 字母标题
        'uppercase': 8,              # 全大写标题
        'chinese_uppercase': 9       # 中文大写标题
    },
    
    # 标题识别模式
    'title_patterns': {
        'markdown': {
            'pattern': r'^(#{1,6})\s+(.+)$',
            'description': 'Markdown标题 (# ## ### 等)',
            'examples': ['# 标题1', '## 标题2', '### 标题3']
        },
        'chinese_chapter': {
            'pattern': r'^第([一二三四五六七八九十\d]+)[章节部分]\s*(.+)$',
            'description': '中文章节标题',
            'examples': ['第一章 绪论', '第二节 背景', '第三部分 方法']
        },
        'chinese_section': {
            'pattern': r'^([一二三四五六七八九十\d]+)\.\s*(.+)$',
            'description': '中文小节标题',
            'examples': ['一. 引言', '二. 方法', '三. 结果']
        },
        'english_chapter': {
            'pattern': r'^Chapter\s+(\d+)(?:\s*[-:]\s*(.+))?$',
            'description': '英文章节标题',
            'examples': ['Chapter 1', 'Chapter 2: Background', 'Chapter 3 - Methods']
        },
        'english_section': {
            'pattern': r'^(\d+)\.(\d+)(?:\s*[-:]\s*(.+))?$',
            'description': '英文小节标题',
            'examples': ['1.1', '2.2 Background', '3.3 - Methods']
        },
        'numeric': {
            'pattern': r'^(\d+)\.\s*(.+)$',
            'description': '数字标题',
            'examples': ['1. 引言', '2. 方法', '3. 结果']
        },
        'alphabetic': {
            'pattern': r'^([A-Z])\.\s*(.+)$',
            'description': '字母标题',
            'examples': ['A. 附录', 'B. 参考文献', 'C. 索引']
        },
        'uppercase': {
            'pattern': r'^([A-Z][A-Z\s]{2,})$',
            'description': '全大写标题',
            'examples': ['ABSTRACT', 'INTRODUCTION', 'METHODOLOGY']
        },
        'chinese_uppercase': {
            'pattern': r'^([一二三四五六七八九十]+)\s*(.+)$',
            'description': '中文大写标题',
            'examples': ['一 绪论', '二 方法', '三 结果']
        }
    },
    
    # 分块策略配置
    'chunking_strategies': {
        'hierarchical': {
            'enabled': True,
            'description': '基于标题层级的层次化分块',
            'max_levels': 6
        },
        'semantic': {
            'enabled': True,
            'description': '基于语义的分块',
            'similarity_threshold': 0.7
        },
        'adaptive': {
            'enabled': True,
            'description': '自适应分块策略',
            'min_chunks': 3,
            'max_chunks': 20
        }
    },
    
    # 后处理配置
    'post_processing': {
        'merge_small_chunks': True,      # 合并过小的分块
        'split_large_chunks': True,      # 分割过大的分块
        'remove_empty_chunks': True,     # 移除空分块
        'normalize_chunk_sizes': True,   # 标准化分块大小
        'validate_chunk_quality': True   # 验证分块质量
    },
    
    # 质量评估配置
    'quality_metrics': {
        'coherence_score': True,         # 连贯性评分
        'completeness_score': True,      # 完整性评分
        'boundary_score': True,          # 边界清晰度评分
        'overlap_score': True            # 重叠度评分
    }
}

# 语言特定配置
LANGUAGE_SPECIFIC_CONFIG = {
    'chinese': {
        'title_patterns': ['chinese_chapter', 'chinese_section', 'chinese_uppercase'],
        'sentence_endings': ['。', '！', '？', '；'],
        'paragraph_separators': ['\n\n', '\r\n\r\n'],
        'priority': 1
    },
    'english': {
        'title_patterns': ['english_chapter', 'english_section', 'alphabetic'],
        'sentence_endings': ['.', '!', '?', ';'],
        'paragraph_separators': ['\n\n', '\r\n\r\n'],
        'priority': 2
    },
    'mixed': {
        'title_patterns': ['markdown', 'numeric', 'uppercase'],
        'sentence_endings': ['.', '!', '?', ';', '。', '！', '？', '；'],
        'paragraph_separators': ['\n\n', '\r\n\r\n'],
        'priority': 3
    }
}

# 文档类型特定配置
DOCUMENT_TYPE_CONFIG = {
    'academic_paper': {
        'expected_structure': ['abstract', 'introduction', 'related_work', 'methodology', 'experiments', 'conclusion'],
        'title_patterns': ['markdown', 'numeric', 'english_section'],
        'chunk_size_range': (500, 3000),
        'priority': 1
    },
    'technical_document': {
        'expected_structure': ['overview', 'installation', 'usage', 'api', 'examples', 'troubleshooting'],
        'title_patterns': ['markdown', 'numeric', 'uppercase'],
        'chunk_size_range': (300, 2000),
        'priority': 2
    },
    'book': {
        'expected_structure': ['preface', 'chapter', 'appendix', 'index'],
        'title_patterns': ['chinese_chapter', 'english_chapter', 'numeric'],
        'chunk_size_range': (1000, 5000),
        'priority': 3
    },
    'report': {
        'expected_structure': ['executive_summary', 'introduction', 'findings', 'conclusions', 'recommendations'],
        'title_patterns': ['markdown', 'uppercase', 'numeric'],
        'chunk_size_range': (800, 2500),
        'priority': 4
    }
}


class ChapterConfig:
    """章节分块配置管理类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or DEFAULT_CHAPTER_CONFIG.copy()
        self._validate_config()
    
    def _validate_config(self):
        """验证配置的有效性"""
        required_keys = ['min_chunk_size', 'max_chunk_size', 'chunk_size']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"缺少必需的配置项: {key}")
        
        # 验证大小关系
        if self.config['min_chunk_size'] >= self.config['max_chunk_size']:
            raise ValueError("min_chunk_size 必须小于 max_chunk_size")
        
        if self.config['chunk_size'] < self.config['min_chunk_size']:
            raise ValueError("chunk_size 不能小于 min_chunk_size")
        
        if self.config['chunk_size'] > self.config['max_chunk_size']:
            raise ValueError("chunk_size 不能大于 max_chunk_size")
    
    def get_title_patterns(self, language: str = None) -> List[str]:
        """获取指定语言的标题模式"""
        if language and language in LANGUAGE_SPECIFIC_CONFIG:
            return LANGUAGE_SPECIFIC_CONFIG[language]['title_patterns']
        return list(self.config['title_patterns'].keys())
    
    def get_document_type_config(self, doc_type: str) -> Dict[str, Any]:
        """获取指定文档类型的配置"""
        return DOCUMENT_TYPE_CONFIG.get(doc_type, {})
    
    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        self.config.update(updates)
        self._validate_config()
    
    def get_config(self, key: str = None) -> Any:
        """获取配置值"""
        if key is None:
            return self.config
        return self.config.get(key)
    
    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否启用"""
        if feature in self.config:
            return bool(self.config[feature])
        return False
    
    def get_quality_metrics(self) -> List[str]:
        """获取启用的质量评估指标"""
        metrics = []
        for metric, enabled in self.config['quality_metrics'].items():
            if enabled:
                metrics.append(metric)
        return metrics


def create_config_for_document_type(doc_type: str, **kwargs) -> ChapterConfig:
    """为指定文档类型创建配置"""
    base_config = DEFAULT_CHAPTER_CONFIG.copy()
    
    if doc_type in DOCUMENT_TYPE_CONFIG:
        doc_config = DOCUMENT_TYPE_CONFIG[doc_type]
        base_config.update(doc_config)
    
    # 应用自定义参数
    base_config.update(kwargs)
    
    return ChapterConfig(base_config)


def create_config_for_language(language: str, **kwargs) -> ChapterConfig:
    """为指定语言创建配置"""
    base_config = DEFAULT_CHAPTER_CONFIG.copy()
    
    if language in LANGUAGE_SPECIFIC_CONFIG:
        lang_config = LANGUAGE_SPECIFIC_CONFIG[language]
        # 根据语言调整标题模式优先级
        for pattern in lang_config['title_patterns']:
            if pattern in base_config['title_pattern_priorities']:
                base_config['title_pattern_priorities'][pattern] = lang_config['priority']
    
    # 应用自定义参数
    base_config.update(kwargs)
    
    return ChapterConfig(base_config)
