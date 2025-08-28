#!/usr/bin/env python3
"""
检查数据库中的用户
"""

import os
import sys
import django

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'zhiqing_server'))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zhiqing_server.settings')
django.setup()

from django.db import connection

def check_users():
    """检查数据库中的用户"""
    try:
        with connection.cursor() as cursor:
            # 检查所有表
            cursor.execute("""
                SHOW TABLES
            """)
            
            tables = cursor.fetchall()
            print(f"📊 数据库中的所有表:")
            print("=" * 80)
            
            for table in tables:
                table_name = table[0]
                print(f"表名: {table_name}")
                
                # 检查表结构
                try:
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    print(f"  列数: {len(columns)}")
                    for col in columns:
                        print(f"    - {col[0]} ({col[1]})")
                    print("-" * 40)
                except Exception as e:
                    print(f"  ⚠️ 无法获取表结构: {str(e)}")
            
            # 检查用户相关的表
            print(f"\n🔍 检查用户相关表:")
            print("=" * 80)
            
            user_tables = [table[0] for table in tables if 'user' in table[0].lower()]
            for table_name in user_tables:
                print(f"\n📋 表: {table_name}")
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    print(f"  记录数: {count}")
                    
                    if count > 0:
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                        rows = cursor.fetchall()
                        for i, row in enumerate(rows):
                            print(f"  记录 {i+1}: {row}")
                            
                except Exception as e:
                    print(f"  ⚠️ 查询失败: {str(e)}")
                    
    except Exception as e:
        print(f"❌ 查询失败: {str(e)}")

if __name__ == "__main__":
    check_users()
