#!/bin/bash

# 停止队列管理功能服务脚本
# 使用方法: ./stop_queue_management.sh

echo "🛑 停止ZhiQing队列管理功能服务"
echo "=================================="

# 停止后端服务
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null; then
        echo "🔄 正在停止后端服务 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        sleep 2
        
        # 强制停止如果还在运行
        if ps -p $BACKEND_PID > /dev/null; then
            echo "⚠️  强制停止后端服务..."
            kill -9 $BACKEND_PID
        fi
        
        echo "✅ 后端服务已停止"
    else
        echo "ℹ️  后端服务进程不存在"
    fi
    rm -f .backend.pid
else
    echo "ℹ️  未找到后端进程ID文件"
fi

# 停止前端服务
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null; then
        echo "🔄 正在停止前端服务 (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        sleep 2
        
        # 强制停止如果还在运行
        if ps -p $FRONTEND_PID > /dev/null; then
            echo "⚠️  强制停止前端服务..."
            kill -9 $FRONTEND_PID
        fi
        
        echo "✅ 前端服务已停止"
    else
        echo "ℹ️  前端服务进程不存在"
    fi
    rm -f .frontend.pid
else
    echo "ℹ️  未找到前端进程ID文件"
fi

# 检查端口占用
echo "🔍 检查端口占用情况..."

# 检查8000端口
if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  端口8000仍被占用，正在清理..."
    lsof -ti :8000 | xargs kill -9
    echo "✅ 端口8000已释放"
else
    echo "✅ 端口8000未被占用"
fi

# 检查8080端口
if lsof -i :8080 > /dev/null 2>&1; then
    echo "⚠️  端口8080仍被占用，正在清理..."
    lsof -ti :8080 | xargs kill -9
    echo "✅ 端口8080已释放"
else
    echo "✅ 端口8080未被占用"
fi

echo ""
echo "🎉 所有服务已停止！"
echo "=================================="
echo "💡 如需重新启动，请运行: ./start_queue_management.sh"
echo ""
