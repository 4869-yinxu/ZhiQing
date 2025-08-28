#!/usr/bin/env python3
"""
检查知识库18的配置
"""

import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zhiqing_server.settings')
django.setup()

print("=== 检查知识库18配置 ===")

try:
    from django.db import connection
    
    # 获取知识库18信息
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT kb.id, kb.name, kb.embedding_model_id, kb.vector_dimension
            FROM knowledge_database kb
            WHERE kb.id = 18
        """)
        kb_info = cursor.fetchone()
        
        if kb_info:
            kb_id, kb_name, embedding_model_id, vector_dimension = kb_info
            print(f"知识库ID: {kb_id}")
            print(f"知识库名称: {kb_name}")
            print(f"Embedding模型ID: {embedding_model_id}")
            print(f"向量维度: {vector_dimension}")
            
            # 获取对应的embedding模型信息
            if embedding_model_id:
                cursor.execute("""
                    SELECT id, name, model_type, api_type, local_path, vector_dimension
                    FROM embedding_model
                    WHERE id = %s
                """, [embedding_model_id])
                model_info = cursor.fetchone()
                
                if model_info:
                    model_id, model_name, model_type, api_type, local_path, model_vector_dim = model_info
                    print(f"\n=== Embedding模型信息 ===")
                    print(f"模型ID: {model_id}")
                    print(f"模型名称: {model_name}")
                    print(f"模型类型: {model_type}")
                    print(f"API类型: {api_type}")
                    print(f"本地路径: {local_path}")
                    print(f"模型向量维度: {model_vector_dim}")
                    
                    # 检查本地路径是否存在
                    if local_path:
                        print(f"本地路径存在: {os.path.exists(local_path)}")
                        if os.path.exists(local_path):
                            try:
                                path_content = os.listdir(local_path)
                                print(f"路径内容: {path_content[:5]}...")  # 只显示前5个
                            except Exception as e:
                                print(f"读取路径内容失败: {e}")
                    
                    print("\n=== 测试模型加载 ===")
                    
                    # 测试模型加载
                    from system_mgt.utils.llms_manager import llms_manager
                    
                    model_config = {
                        'model_type': model_type,
                        'name': model_name,
                        'local_path': local_path,
                        'api_key': None,  # 暂时设为None
                        'api_url': None,   # 暂时设为None
                        'vector_dimension': model_vector_dim
                    }
                    
                    print(f"模型配置: {model_config}")
                    
                    # 尝试加载模型
                    success = llms_manager.load_knowledge_base_model(18, model_config)
                    print(f"模型加载结果: {'成功' if success else '失败'}")
                    
                    if success:
                        # 测试embedding生成
                        test_text = "这是一个测试文本"
                        result = llms_manager.test_embedding(test_text)
                        print(f"Embedding测试结果: {result}")
                else:
                    print(f"❌ 未找到ID为 {embedding_model_id} 的embedding模型")
            else:
                print("❌ 知识库18没有关联的embedding模型")
        else:
            print("❌ 未找到ID为18的知识库")
    
except Exception as e:
    print(f"检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 检查完成 ===")
