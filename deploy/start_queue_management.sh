#!/bin/bash

# 启动队列管理功能测试脚本
# 使用方法: ./start_queue_management.sh

echo "🚀 启动ZhiQing队列管理功能测试"
echo "=================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "📦 检查Python依赖..."
if ! python3 -c "import requests" &> /dev/null; then
    echo "⚠️  requests 模块未安装，正在安装..."
    pip3 install requests
fi

# 检查后端服务状态
echo "🔍 检查后端服务状态..."
if ! curl -s http://localhost:8000/api/health/ &> /dev/null; then
    echo "⚠️  后端服务未运行，正在启动..."
    cd zhiqing_server
    python3 manage.py runserver 8000 &
    BACKEND_PID=$!
    echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
    sleep 5  # 等待服务启动
    cd ..
else
    echo "✅ 后端服务正在运行"
fi

# 检查前端服务状态
echo "🔍 检查前端服务状态..."
if ! curl -s http://localhost:8080 &> /dev/null; then
    echo "⚠️  前端服务未运行，正在启动..."
    cd zhiqing_ui
    npm run serve &
    FRONTEND_PID=$!
    echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
    sleep 10  # 等待服务启动
    cd ..
else
    echo "✅ 前端服务正在运行"
fi

# 等待服务完全启动
echo "⏳ 等待服务完全启动..."
sleep 5

# 检查服务状态
echo "🔍 最终服务状态检查..."
if curl -s http://localhost:8000/api/health/ &> /dev/null; then
    echo "✅ 后端服务运行正常"
else
    echo "❌ 后端服务启动失败"
    exit 1
fi

if curl -s http://localhost:8080 &> /dev/null; then
    echo "✅ 前端服务运行正常"
else
    echo "❌ 前端服务启动失败"
    exit 1
fi

echo ""
echo "🎉 所有服务启动成功！"
echo "=================================="
echo "🌐 前端地址: http://localhost:8080"
echo "🔧 后端地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/api/docs/"
echo ""

# 询问是否运行测试
read -p "是否运行队列管理功能测试？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧪 开始运行测试..."
    python3 test_queue_management.py
else
    echo "💡 可以稍后手动运行: python3 test_queue_management.py"
fi

echo ""
echo "📋 使用说明:"
echo "1. 访问前端界面: http://localhost:8080"
echo "2. 登录系统，进入文档管理页面"
echo "3. 查看上传队列，测试删除、取消、清空功能"
echo "4. 运行测试脚本: python3 test_queue_management.py"
echo ""

# 保存进程ID
if [ ! -z "$BACKEND_PID" ]; then
    echo $BACKEND_PID > .backend.pid
    echo "💾 后端进程ID已保存到 .backend.pid"
fi

if [ ! -z "$FRONTEND_PID" ]; then
    echo $FRONTEND_PID > .frontend.pid
    echo "💾 前端进程ID已保存到 .frontend.pid"
fi

echo "🔄 服务将在后台运行，使用以下命令停止:"
echo "   ./stop_queue_management.sh"
echo ""
echo "✨ 队列管理功能已就绪！"
