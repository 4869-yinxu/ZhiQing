#!/usr/bin/env python3
"""
更新数据库结构
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

def update_database():
    """更新数据库结构"""
    try:
        with connection.cursor() as cursor:
            print("🔧 开始更新数据库结构...")
            
            # 1. 检查当前状态枚举
            print("\n📊 检查当前状态枚举...")
            cursor.execute("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'document_upload_task' 
                  AND COLUMN_NAME = 'status'
            """)
            
            result = cursor.fetchone()
            if result:
                print(f"当前状态枚举: {result[0]}")
            else:
                print("❌ 无法获取状态枚举信息")
                return
            
            # 2. 更新状态枚举，添加 cancelled 状态
            print("\n🔄 更新状态枚举...")
            try:
                cursor.execute("""
                    ALTER TABLE `document_upload_task` 
                    MODIFY COLUMN `status` enum('pending','processing','completed','failed','cancelled') DEFAULT 'pending' COMMENT '任务状态'
                """)
                print("✅ 状态枚举更新成功")
            except Exception as e:
                print(f"⚠️ 状态枚举更新失败（可能已经是最新版本）: {str(e)}")
            
            # 3. 验证更新结果
            print("\n✅ 验证更新结果...")
            cursor.execute("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'document_upload_task' 
                  AND COLUMN_NAME = 'status'
            """)
            
            result = cursor.fetchone()
            if result:
                print(f"更新后状态枚举: {result[0]}")
            else:
                print("❌ 无法获取更新后的状态枚举信息")
            
            # 4. 查看当前任务状态分布
            print("\n📋 查看当前任务状态分布...")
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM document_upload_task 
                GROUP BY status
            """)
            
            status_counts = cursor.fetchall()
            if status_counts:
                print("任务状态分布:")
                for status, count in status_counts:
                    print(f"  - {status}: {count}")
            else:
                print("暂无任务数据")
            
            # 5. 查看用户表结构
            print("\n👥 查看用户表结构...")
            cursor.execute("DESCRIBE user")
            columns = cursor.fetchall()
            print("用户表结构:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]})")
            
            # 6. 查看角色表
            print("\n🎭 查看角色表...")
            cursor.execute("SELECT * FROM role")
            roles = cursor.fetchall()
            print("角色表数据:")
            for role in roles:
                print(f"  - ID: {role[0]}, 名称: {role[1]}, 描述: {role[2]}")
            
            print("\n🎉 数据库结构更新完成！")
            
    except Exception as e:
        print(f"❌ 更新失败: {str(e)}")

if __name__ == "__main__":
    update_database()


