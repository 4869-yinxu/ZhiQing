#!/usr/bin/env python3
"""
调试处理器选择问题
"""

import os
import sys
import django

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'zhiqing_server'))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zhiqing_server.settings')
django.setup()

from knowledge_mgt.utils.document_processor.processor_factory import get_processor_info, get_document_processor

def debug_processor_selection():
    """调试处理器选择问题"""
    try:
        print("🔧 开始调试处理器选择问题...")
        
        # 1. 检查环境变量
        print("\n📋 环境变量检查:")
        llama_cloud_key = os.environ.get('LLAMA_CLOUD_API_KEY')
        llama_parse_key = os.environ.get('LLAMA_PARSE_API_KEY')
        
        print(f"  - LLAMA_CLOUD_API_KEY: {'已设置' if llama_cloud_key else '未设置'}")
        print(f"  - LLAMA_PARSE_API_KEY: {'已设置' if llama_parse_key else '未设置'}")
        
        if not llama_cloud_key and not llama_parse_key:
            print("  ⚠️  LlamaParse API key 未设置，将无法使用 LlamaParse 处理器")
        
        # 2. 获取处理器信息
        print("\n🔍 处理器信息:")
        processor_info = get_processor_info()
        
        for proc_type, info in processor_info.items():
            print(f"  - {proc_type}:")
            print(f"    - 名称: {info.get('name', 'N/A')}")
            print(f"    - 可用: {info.get('available', False)}")
            print(f"    - 支持格式: {info.get('supported_formats', [])}")
            if not info.get('available'):
                print(f"    - 错误: {info.get('error', 'N/A')}")
        
        # 3. 测试Excel文件处理
        print("\n📊 测试Excel文件处理:")
        test_file = "test.xlsx"
        
        try:
            processor = get_document_processor(test_file)
            print(f"  ✅ 自动选择处理器: {processor.processor_name}")
            print(f"  - 类型: {type(processor).__name__}")
            print(f"  - 可用: {processor.is_available()}")
            print(f"  - 可处理: {processor.can_process(test_file)}")
            print(f"  - 支持格式: {processor.get_supported_formats()}")
            
        except Exception as e:
            print(f"  ❌ 获取处理器失败: {str(e)}")
        
        # 4. 检查处理器优先级
        print("\n🎯 处理器优先级分析:")
        print("  1. LlamaParseProcessor (最新最强大)")
        print("  2. LlamaIndexProcessor (功能丰富)")
        print("  3. LegacyDocumentProcessor (兼容性最好)")
        
        # 5. 建议
        print("\n💡 建议:")
        if not llama_cloud_key and not llama_parse_key:
            print("  - 设置 LLAMA_CLOUD_API_KEY 或 LLAMA_PARSE_API_KEY 环境变量")
            print("  - 这样可以使用 LlamaParse 处理器来处理 Excel 文件")
        else:
            print("  - API key 已设置，检查 LlamaParse 处理器是否正确初始化")
        
        print("  - 确保 LlamaParse 处理器在处理器工厂中正确注册")
        print("  - 检查处理器工厂的自动选择逻辑")
        
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")

if __name__ == "__main__":
    debug_processor_selection()
