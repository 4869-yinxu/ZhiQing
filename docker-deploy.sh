#!/bin/bash

# ZhiQing Docker部署脚本
# 使用方法: ./docker-deploy.sh [dev|prod]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
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
    echo -e "${BLUE}  ZhiQing Docker 部署脚本${NC}"
    echo -e "${BLUE}================================${NC}"
}

# 检查Docker是否安装
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

# 检查环境变量文件
check_env_file() {
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            print_warning "未找到 .env 文件，从 env.example 创建"
            cp env.example .env
            print_warning "请编辑 .env 文件配置环境变量"
        else
            print_error "未找到环境变量文件"
            exit 1
        fi
    fi
    print_message "环境变量文件检查通过"
}

# 创建必要的目录
create_directories() {
    print_message "创建必要的目录..."
    mkdir -p data models media logs ssl
    print_message "目录创建完成"
}

# 开发环境部署
deploy_dev() {
    print_message "开始开发环境部署..."
    
    # 停止现有容器
    docker-compose down 2>/dev/null || true
    
    # 构建并启动服务
    docker-compose up -d --build
    
    print_message "开发环境部署完成"
    print_message "服务访问地址："
    echo "  - 前端: http://localhost:80"
    echo "  - 后端: http://localhost:8000"
    echo "  - 数据库: localhost:3306"
    echo "  - Redis: localhost:6379"
}

# 生产环境部署
deploy_prod() {
    print_message "开始生产环境部署..."
    
    # 检查SSL证书
    if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
        print_warning "未找到SSL证书文件，将使用HTTP模式"
        print_warning "生产环境建议配置SSL证书"
    fi
    
    # 停止现有容器
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # 构建并启动服务
    docker-compose -f docker-compose.prod.yml up -d --build
    
    print_message "生产环境部署完成"
    print_message "服务访问地址："
    echo "  - 应用: https://localhost (如果配置了SSL)"
    echo "  - 应用: http://localhost (HTTP模式)"
}

# 显示服务状态
show_status() {
    print_message "服务状态："
    if [ "$1" = "prod" ]; then
        docker-compose -f docker-compose.prod.yml ps
    else
        docker-compose ps
    fi
}

# 显示日志
show_logs() {
    print_message "显示服务日志："
    if [ "$1" = "prod" ]; then
        docker-compose -f docker-compose.prod.yml logs -f
    else
        docker-compose logs -f
    fi
}

# 清理资源
cleanup() {
    print_message "清理Docker资源..."
    if [ "$1" = "prod" ]; then
        docker-compose -f docker-compose.prod.yml down -v
    else
        docker-compose down -v
    fi
    docker system prune -f
    print_message "清理完成"
}

# 主函数
main() {
    print_header
    
    # 检查参数
    ENV=${1:-dev}
    
    if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
        print_error "无效的环境参数，请使用 'dev' 或 'prod'"
        echo "使用方法: $0 [dev|prod]"
        exit 1
    fi
    
    print_message "部署环境: $ENV"
    
    # 执行检查
    check_docker
    check_env_file
    create_directories
    
    # 根据环境部署
    if [ "$ENV" = "prod" ]; then
        deploy_prod
    else
        deploy_dev
    fi
    
    # 等待服务启动
    print_message "等待服务启动..."
    sleep 10
    
    # 显示状态
    show_status $ENV
    
    print_message "部署完成！"
    echo ""
    echo "常用命令："
    echo "  查看日志: $0 logs $ENV"
    echo "  查看状态: $0 status $ENV"
    echo "  清理资源: $0 cleanup $ENV"
}

# 处理子命令
case "$1" in
    "logs")
        show_logs $2
        ;;
    "status")
        show_status $2
        ;;
    "cleanup")
        cleanup $2
        ;;
    *)
        main $1
        ;;
esac
