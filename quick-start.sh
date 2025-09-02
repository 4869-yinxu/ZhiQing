#!/bin/bash

# ZhiQing 快速启动脚本
# 用于快速部署和启动ZhiQing系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  ZhiQing 快速启动脚本${NC}"
    echo -e "${BLUE}================================${NC}"
}

# 检查Docker环境
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_message "Docker 环境检查通过"
}

# 初始化环境
init_environment() {
    print_message "初始化环境..."
    
    # 创建必要的目录
    mkdir -p data models media logs ssl
    
    # 检查环境变量文件
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            print_warning "未找到 .env 文件，从 env.example 创建"
            cp env.example .env
            print_warning "请根据需要编辑 .env 文件"
        else
            print_error "未找到环境变量模板文件"
            exit 1
        fi
    fi
    
    print_message "环境初始化完成"
}

# 启动服务
start_services() {
    print_message "启动 ZhiQing 服务..."
    
    # 停止现有容器
    docker-compose down 2>/dev/null || true
    
    # 构建并启动服务
    docker-compose up -d --build
    
    print_message "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    print_message "等待服务就绪..."
    
    # 等待数据库启动
    print_message "等待数据库启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T mysql mysqladmin ping -h localhost --silent; then
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "数据库启动超时"
        exit 1
    fi
    
    # 等待后端服务启动
    print_message "等待后端服务启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:8000/health/simple/ >/dev/null 2>&1; then
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "后端服务启动超时"
        exit 1
    fi
    
    print_message "所有服务已就绪"
}

# 显示服务状态
show_status() {
    print_message "服务状态："
    docker-compose ps
    
    echo ""
    print_message "服务访问地址："
    echo "  - 前端应用: http://localhost:80"
    echo "  - 后端API: http://localhost:8000"
    echo "  - 健康检查: http://localhost:8000/health/"
    echo "  - 管理后台: http://localhost:8000/admin/"
    echo "  - 数据库: localhost:3306"
    echo "  - Redis: localhost:6379"
}

# 主函数
main() {
    print_header
    
    check_docker
    init_environment
    start_services
    wait_for_services
    show_status
    
    echo ""
    print_message "ZhiQing 系统启动完成！"
    echo ""
    echo "常用命令："
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
    echo "  进入容器: docker-compose exec backend bash"
}

# 执行主函数
main "$@"
