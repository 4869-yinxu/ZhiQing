#!/usr/bin/env python3
"""
调试取消任务API
"""

import requests
import json

# 配置
BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/account/login"
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin123"

def debug_cancel_task():
    """调试取消任务API"""
    
    # 1. 登录获取token
    print("🔐 正在登录...")
    session = requests.Session()
    
    login_data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    try:
        response = session.post(LOGIN_URL, json=login_data)
        print(f"登录响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"登录响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get('code') == 200:
                token = data.get('data', {}).get('token')
                print(f"✅ 登录成功，获取到token: {token[:20]}...")
            else:
                print(f"❌ 登录失败: {data.get('message')}")
                return
        else:
            print(f"❌ 登录请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ 登录异常: {str(e)}")
        return
    
    # 2. 获取任务列表
    print("\n📋 获取任务列表...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = session.get(f"{BASE_URL}/knowledge/upload-task/list/", headers=headers)
        print(f"获取任务列表响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"任务列表响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get('code') == 200 and data.get('data', {}).get('tasks'):
                tasks = data['data']['tasks']
                print(f"✅ 获取到 {len(tasks)} 个任务")
                
                # 查找处理中的任务
                processing_tasks = [task for task in tasks if task.get('status') == 'processing']
                if processing_tasks:
                    test_task = processing_tasks[0]
                    print(f"✅ 找到处理中的任务: {test_task.get('filename')} (ID: {test_task.get('task_id')})")
                    
                    # 3. 测试取消任务
                    print(f"\n⏹️ 测试取消任务: {test_task.get('task_id')}")
                    cancel_url = f"{BASE_URL}/knowledge/upload-task/{test_task.get('task_id')}/cancel/"
                    print(f"取消任务URL: {cancel_url}")
                    
                    response = session.post(cancel_url, headers=headers)
                    print(f"取消任务响应状态: {response.status_code}")
                    print(f"取消任务响应头: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ 取消任务成功: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    else:
                        print(f"❌ 取消任务失败: {response.status_code}")
                        print(f"响应内容: {response.text}")
                        
                        # 尝试获取任务详情
                        print(f"\n🔍 获取任务详情...")
                        detail_url = f"{BASE_URL}/knowledge/upload-task/{test_task.get('task_id')}/detail/"
                        response = session.get(detail_url, headers=headers)
                        print(f"获取任务详情响应状态: {response.status_code}")
                        
                        if response.status_code == 200:
                            data = response.json()
                            print(f"任务详情: {json.dumps(data, indent=2, ensure_ascii=False)}")
                        else:
                            print(f"获取任务详情失败: {response.text}")
                else:
                    print("⚠️ 没有找到处理中的任务")
                    
                    # 显示所有任务状态
                    print("\n📊 所有任务状态:")
                    for task in tasks:
                        print(f"  - {task.get('filename')}: {task.get('status')}")
            else:
                print(f"❌ 获取任务列表失败: {data.get('message')}")
        else:
            print(f"❌ 获取任务列表请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 获取任务列表异常: {str(e)}")

if __name__ == "__main__":
    debug_cancel_task()
