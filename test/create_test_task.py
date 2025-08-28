#!/usr/bin/env python3
"""
创建测试任务
"""

import os
import sys
import django
import uuid
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'zhiqing_server'))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zhiqing_server.settings')
django.setup()

from django.db import connection

def create_test_task():
    """创建测试任务"""
    try:
        with connection.cursor() as cursor:
            print("🔧 开始创建测试任务...")
            
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 创建处理中的任务
            cursor.execute("""
                INSERT INTO document_upload_task (
                    task_id, user_id, username, database_id, filename, file_path, 
                    file_size, chunking_method, chunk_size, similarity_threshold,
                    overlap_size, custom_delimiter, window_size, step_size,
                    min_chunk_size, max_chunk_size, status, progress,
                    created_at, updated_at, started_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                task_id,           # task_id
                10,                # user_id (admin)
                'admin',           # username
                1,                 # database_id
                'test_processing.pdf',  # filename
                '/tmp/test.pdf',   # file_path
                1024000,           # file_size
                'semantic',        # chunking_method
                500,               # chunk_size
                0.7,               # similarity_threshold
                100,               # overlap_size
                '\n\n',            # custom_delimiter
                3,                 # window_size
                1,                 # step_size
                50,                # min_chunk_size
                2000,              # max_chunk_size
                'processing',      # status
                45,                # progress
                datetime.now(),    # created_at
                datetime.now(),    # updated_at
                datetime.now()     # started_at
            ])
            
            print(f"✅ 成功创建测试任务:")
            print(f"  - 任务ID: {task_id}")
            print(f"  - 文件名: test_processing.pdf")
            print(f"  - 状态: processing")
            print(f"  - 进度: 45%")
            
            # 验证任务创建
            cursor.execute("SELECT * FROM document_upload_task WHERE task_id = %s", [task_id])
            task = cursor.fetchone()
            if task:
                print(f"\n📋 任务信息:")
                print(f"  - 完整记录: {task}")
            
            return task_id
            
    except Exception as e:
        print(f"❌ 创建任务失败: {str(e)}")
        return None

if __name__ == "__main__":
    create_test_task()
