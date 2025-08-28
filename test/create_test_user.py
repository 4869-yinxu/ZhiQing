#!/usr/bin/env python3
"""
创建测试用户
"""

import os
import sys
import django
import bcrypt

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'zhiqing_server'))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zhiqing_server.settings')
django.setup()

from django.db import connection

def create_test_user():
    """创建测试用户"""
    try:
        with connection.cursor() as cursor:
            print("🔧 开始创建测试用户...")
            
            # 检查用户是否已存在
            cursor.execute("SELECT COUNT(*) FROM user WHERE username = 'admin'")
            count = cursor.fetchone()[0]
            
            if count > 0:
                print("⚠️ 用户 'admin' 已存在")
                return
            
            # 创建管理员用户
            username = 'admin'
            password = 'admin123'
            email = 'admin@example.com'
            role_id = 1  # 管理员角色
            
            # 加密密码 - 使用与系统一致的加密方式
            from zhiqing_server.settings import SECRET_KEY
            hashed_password = bcrypt.hashpw((password + SECRET_KEY).encode('utf-8'), bcrypt.gensalt())
            
            # 插入用户
            cursor.execute("""
                INSERT INTO user (username, password, email, role_id, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """, [username, hashed_password.decode('utf-8'), email, role_id, 1])
            
            user_id = cursor.lastrowid
            print(f"✅ 成功创建用户:")
            print(f"  - ID: {user_id}")
            print(f"  - 用户名: {username}")
            print(f"  - 密码: {password}")
            print(f"  - 邮箱: {email}")
            print(f"  - 角色ID: {role_id}")
            
            # 验证用户创建
            cursor.execute("SELECT * FROM user WHERE username = %s", [username])
            user = cursor.fetchone()
            if user:
                print(f"\n📋 用户信息:")
                print(f"  - 完整记录: {user}")
            
    except Exception as e:
        print(f"❌ 创建用户失败: {str(e)}")

if __name__ == "__main__":
    create_test_user()
