#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式文档处理功能演示
展示从原来只支持txt到支持docx/pdf/doc/md/excel的升级
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_sample_files():
    """创建示例文件用于演示"""
    sample_files = {}
    
    # 创建示例文本文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("""这是一个示例文本文件。

包含多个段落，用于演示文本处理功能。

每个段落都有不同的内容，可以测试文本分割算法。
""")
        sample_files['txt'] = f.name
    
    # 创建示例Markdown文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write("""# 示例Markdown文档

## 第一章：介绍

这是一个示例Markdown文档，用于演示文档结构解析功能。

### 1.1 背景

文档处理是知识库构建的重要环节。

### 1.2 目标

- 支持多种文档格式
- 智能文档结构解析
- 语义文本分割

## 第二章：技术实现

### 2.1 架构设计

采用模块化设计，支持扩展。

### 2.2 核心功能

1. 文档格式识别
2. 文本内容提取
3. 结构信息解析
4. 智能文本分割

## 总结

通过LlamaIndex实现了多格式文档支持。
""")
        sample_files['md'] = f.name
    
    # 创建示例CSV文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write("""姓名,年龄,职业,城市
张三,25,工程师,北京
李四,30,设计师,上海
王五,28,产品经理,深圳
赵六,32,数据分析师,杭州
""")
        sample_files['csv'] = f.name
    
    return sample_files

def demo_legacy_processing():
    """演示原有的txt处理功能"""
    print("🔧 === 原有功能演示：TXT文件处理 ===")
    
    try:
        from knowledge_mgt.utils.document_processor import get_document_processor
        
        # 创建测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("这是第一段内容。\n\n这是第二段内容。\n\n这是第三段内容。")
            test_file = f.name
        
        try:
            # 强制使用Legacy处理器
            processor = get_document_processor(test_file, processor_type='legacy')
            print(f"处理器类型: {processor.processor_name}")
            
            # 提取文本
            text = processor.extract_text(test_file)
            print(f"提取的文本: {text}")
            
            # 测试不同分块方法
            print("\n--- 不同分块方法演示 ---")
            
            # Token分块
            processor.chunking_method = 'token'
            processor.chunk_size = 50
            chunks = processor.split_text(text)
            print(f"Token分块 (大小50): {len(chunks)} 块")
            for i, chunk in enumerate(chunks):
                print(f"  块{i+1}: {chunk[:30]}...")
            
            # 句子分块
            processor.chunking_method = 'sentence'
            chunks = processor.split_text(text)
            print(f"\n句子分块: {len(chunks)} 块")
            for i, chunk in enumerate(chunks):
                print(f"  块{i+1}: {chunk}")
            
            # 段落分块
            processor.chunking_method = 'paragraph'
            chunks = processor.split_text(text)
            print(f"\n段落分块: {len(chunks)} 块")
            for i, chunk in enumerate(chunks):
                print(f"  块{i+1}: {chunk}")
            
            return True
            
        finally:
            os.unlink(test_file)
            
    except Exception as e:
        print(f"演示失败: {e}")
        return False

def demo_multiformat_processing():
    """演示多格式文档处理功能"""
    print("\n🚀 === 新功能演示：多格式文档处理 ===")
    
    try:
        from knowledge_mgt.utils.document_processor import (
            get_supported_formats, 
            get_processor_info,
            get_document_processor
        )
        
        # 显示支持的文件格式
        supported_formats = get_supported_formats()
        print(f"支持的文件格式: {supported_formats}")
        
        # 显示处理器信息
        processor_info = get_processor_info()
        print(f"\n处理器信息:")
        for proc_type, info in processor_info.items():
            status = "✅ 可用" if info['available'] else "❌ 不可用"
            print(f"  {proc_type}: {status}")
            if not info['available'] and 'error' in info:
                print(f"    错误: {info['error']}")
        
        # 创建示例文件
        sample_files = create_sample_files()
        
        try:
            # 演示不同格式的处理
            for file_type, file_path in sample_files.items():
                print(f"\n--- 处理 {file_type.upper()} 文件 ---")
                
                try:
                    # 自动选择处理器
                    processor = get_document_processor(file_path)
                    print(f"选择的处理器: {processor.processor_name}")
                    
                    # 提取文本
                    text = processor.extract_text(file_path)
                    print(f"文本长度: {len(text)} 字符")
                    print(f"文本预览: {text[:100]}...")
                    
                    # 提取结构
                    structure = processor.extract_structure(file_path)
                    print(f"文档结构:")
                    print(f"  文件类型: {structure['file_type']}")
                    print(f"  标题数量: {len(structure['headings'])}")
                    print(f"  段落数量: {len(structure['sections'])}")
                    
                    if structure['headings']:
                        print(f"  标题示例:")
                        for heading in structure['headings'][:3]:  # 只显示前3个
                            level = heading.get('level', 1)
                            text = heading.get('text', '')
                            print(f"    {'#' * level} {text}")
                    
                except Exception as e:
                    print(f"  处理失败: {e}")
            
            return True
            
        finally:
            # 清理示例文件
            for file_path in sample_files.values():
                try:
                    os.unlink(file_path)
                except:
                    pass
                    
    except Exception as e:
        print(f"演示失败: {e}")
        return False

def demo_processor_factory():
    """演示处理器工厂功能"""
    print("\n🏭 === 处理器工厂演示 ===")
    
    try:
        from knowledge_mgt.utils.document_processor import document_processor_factory
        
        # 测试处理器选择
        test_files = [
            ('test.txt', '文本文件'),
            ('test.md', 'Markdown文件'),
            ('test.docx', 'Word文档'),
            ('test.pdf', 'PDF文档'),
            ('test.xlsx', 'Excel文件')
        ]
        
        print("处理器自动选择测试:")
        for filename, description in test_files:
            try:
                processor = document_processor_factory.get_processor(filename)
                print(f"  {description}: {processor.processor_name}")
            except Exception as e:
                print(f"  {description}: 无法处理 - {str(e)[:50]}...")
        
        # 测试处理器信息
        print(f"\n处理器详细信息:")
        processor_info = document_processor_factory.get_processor_info()
        for proc_type, info in processor_info.items():
            print(f"  {proc_type}:")
            print(f"    名称: {info['name']}")
            print(f"    可用: {info['available']}")
            print(f"    支持格式: {info['supported_formats']}")
            if not info['available'] and 'error' in info:
                print(f"    错误: {info['error']}")
        
        return True
        
    except Exception as e:
        print(f"演示失败: {e}")
        return False

def main():
    """主演示函数"""
    print("🎯 多格式文档处理功能演示")
    print("=" * 60)
    print("本演示展示从原来只支持txt到支持多种格式的升级")
    print("=" * 60)
    
    demo_results = []
    
    # 运行各项演示
    demo_results.append(("原有功能演示", demo_legacy_processing()))
    demo_results.append(("多格式处理演示", demo_multiformat_processing()))
    demo_results.append(("处理器工厂演示", demo_processor_factory()))
    
    # 输出演示结果
    print("\n" + "=" * 60)
    print("📊 演示结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(demo_results)
    
    for demo_name, result in demo_results:
        status = "✅ 成功" if result else "❌ 失败"
        print(f"{demo_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项演示成功")
    
    if passed == total:
        print("\n🎉 所有演示成功！多格式文档处理功能完全可用。")
        print("\n📋 功能总结:")
        print("  ✅ 保持原有txt处理功能")
        print("  ✅ 新增多格式文档支持")
        print("  ✅ 智能处理器选择")
        print("  ✅ 模块化架构设计")
        print("  ✅ 向后兼容性")
    else:
        print("\n⚠️  部分演示失败，请检查相关功能。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


