# 章节分块功能说明

## 概述

本章节分块功能是基于标题层级的智能文档分块系统，能够自动识别各种格式的标题并进行结构化的文档分割。

## 主要特性

### 🎯 智能标题识别
- **Markdown格式**: `# 标题1`, `## 标题2`, `### 标题3` 等
- **中文章节**: `第一章 绪论`, `第二节 背景`, `第三部分 方法` 等
- **英文章节**: `Chapter 1 Introduction`, `Section 2 Background` 等
- **数字标题**: `1. 引言`, `2.1 问题描述` 等
- **字母标题**: `A. 附录`, `B. 参考文献` 等
- **全大写标题**: `ABSTRACT`, `INTRODUCTION`, `METHODOLOGY` 等

### 🔧 灵活配置
- 支持多种文档类型（学术论文、技术文档、书籍、报告等）
- 支持多语言（中文、英文、混合语言）
- 可配置的分块大小和策略
- 智能回退机制

### 📊 质量保证
- 自动验证分块质量
- 智能合并过小的分块
- 自动分割过大的章节
- 保持语义完整性

## 使用方法

### 1. 基本使用

```python
from knowledge_mgt.utils.document_processor.chapter_processor import ChapterProcessor

# 创建处理器
config = {
    'chunk_size': 1000,
    'min_chunk_size': 50,
    'max_chunk_size': 3000,
    'max_chapter_size': 5000
}

processor = ChapterProcessor(config)

# 分块处理
text = "你的文档内容..."
chunks = processor.split_text(text)
```

### 2. 按文档类型配置

```python
from knowledge_mgt.utils.document_processor.chapter_config import create_config_for_document_type

# 为学术论文创建配置
config = create_config_for_document_type('academic_paper', chunk_size=800)
processor = ChapterProcessor(config)

# 为技术文档创建配置
config = create_config_for_document_type('technical_document', chunk_size=500)
processor = ChapterProcessor(config)
```

### 3. 按语言配置

```python
from knowledge_mgt.utils.document_processor.chapter_config import create_config_for_language

# 为中文文档创建配置
config = create_config_for_language('chinese', chunk_size=1000)
processor = ChapterProcessor(config)

# 为英文文档创建配置
config = create_config_for_language('english', chunk_size=800)
processor = ChapterProcessor(config)
```

### 4. 获取章节摘要

```python
# 获取文档的章节结构摘要
summary = processor.get_chapter_summary(text)
print(f"总标题数: {summary['total_titles']}")
print(f"标题类型: {summary['title_types']}")
print(f"层级结构: {summary['hierarchy_levels']}")
```

## 配置选项

### 基本配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 1000 | 目标分块大小（字符数） |
| `min_chunk_size` | 50 | 最小分块大小（字符数） |
| `max_chunk_size` | 2000 | 最大分块大小（字符数） |
| `max_chapter_size` | 5000 | 最大章节大小（字符数） |

### 高级配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `hierarchy_detection` | True | 是否启用层级检测 |
| `merge_small_chapters` | True | 是否合并过小的章节 |
| `smart_title_detection` | True | 是否启用智能标题检测 |

### 质量评估配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `coherence_score` | True | 连贯性评分 |
| `completeness_score` | True | 完整性评分 |
| `boundary_score` | True | 边界清晰度评分 |
| `overlap_score` | True | 重叠度评分 |

## 支持的文件格式

### 文档类型
- **学术论文**: 支持标准的学术论文结构
- **技术文档**: 支持API文档、用户手册等
- **书籍**: 支持章节结构明显的书籍
- **报告**: 支持商业报告、技术报告等

### 文件格式
- **文本文件**: `.txt`, `.md`, `.markdown`
- **Word文档**: `.docx`, `.doc`
- **PDF文档**: `.pdf`
- **其他格式**: 通过相应的处理器支持

## 分块策略

### 1. 层次化分块
基于标题层级进行智能分块，保持文档的逻辑结构。

### 2. 语义分块
当标题结构不明显时，基于语义相似性进行分块。

### 3. 自适应分块
根据文档内容自动调整分块策略，确保分块质量。

## 质量保证

### 自动验证
- 检查分块大小是否在合理范围内
- 验证分块的语义完整性
- 确保分块边界的合理性

### 智能优化
- 自动合并过小的分块
- 智能分割过大的章节
- 保持分块间的逻辑连贯性

## 性能优化

### 缓存机制
- 标题模式编译缓存
- 分块结果缓存
- 配置参数缓存

### 并行处理
- 支持多线程分块处理
- 异步分块处理
- 批量文档处理

## 错误处理

### 异常情况
- 无标题结构：自动回退到段落分块
- 超大章节：自动分割处理
- 格式错误：智能容错处理

### 日志记录
- 详细的处理日志
- 错误信息记录
- 性能统计信息

## 扩展开发

### 添加新的标题模式

```python
# 在 chapter_config.py 中添加新的标题模式
'custom_pattern': {
    'pattern': r'^你的正则表达式$',
    'type': 'custom_type',
    'level_extractor': lambda m: 1,
    'title_extractor': lambda m: m.group(1),
    'priority': 10
}
```

### 添加新的分块策略

```python
# 在 ChapterProcessor 中添加新的分块方法
def _split_by_custom_strategy(self, text: str) -> List[str]:
    # 实现你的分块逻辑
    pass
```

## 测试

### 运行测试

```bash
# 运行章节分块测试
python test_chapter_chunking.py

# 运行特定测试
python -m pytest test_chapter_chunking.py::test_chapter_processor
```

### 测试用例

- **Markdown文档**: 测试Markdown标题识别
- **中文章节**: 测试中文章节标题识别
- **英文章节**: 测试英文章节标题识别
- **混合格式**: 测试多种格式混合的文档
- **边界情况**: 测试无标题、单章节、超大章节等情况

## 常见问题

### Q: 如何处理没有明显标题结构的文档？
A: 系统会自动检测标题结构，如果没有检测到，会回退到段落分块。

### Q: 如何调整分块大小？
A: 通过配置参数 `chunk_size`、`min_chunk_size`、`max_chunk_size` 来调整。

### Q: 支持哪些语言？
A: 目前支持中文、英文和混合语言，可以通过配置进行扩展。

### Q: 如何处理超大章节？
A: 系统会自动检测超大章节并进行智能分割，确保每个分块都在合理大小范围内。

## 更新日志

### v2.0.0 (当前版本)
- ✅ 新增专门的章节处理器
- ✅ 支持多种标题格式识别
- ✅ 智能分块策略
- ✅ 质量评估系统
- ✅ 灵活的配置管理
- ✅ 完善的错误处理

### v1.0.0 (原版本)
- ✅ 基础章节分块功能
- ✅ 简单的标题识别
- ✅ 基本的分块逻辑

## 贡献指南

欢迎提交Issue和Pull Request来改进这个功能！

### 贡献方式
1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

### 代码规范
- 遵循PEP 8规范
- 添加适当的注释和文档
- 编写测试用例
- 更新相关文档
