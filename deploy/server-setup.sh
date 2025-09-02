#!/bin/bash

# 服务器端安装脚本
# 在服务器上直接执行此脚本
# 
# ⚠️ 重要：使用前请修改以下配置
# 1. 将脚本中的"您的数据库密码"替换为实际的数据库密码
# 2. 确保服务器已安装MySQL、Python3、Node.js等基础环境

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== 开始安装 ZhiQing 系统 ===${NC}"

# 1. 更新系统并安装基础软件
echo -e "${YELLOW}步骤1: 更新系统并安装基础软件...${NC}"
apt update -y
apt install -y curl wget git unzip

# 2. 安装MySQL
echo -e "${YELLOW}步骤2: 安装MySQL...${NC}"
apt install -y mysql-server

# 启动MySQL服务
systemctl start mysql
systemctl enable mysql

# 设置MySQL root密码
echo "设置MySQL root密码..."
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '您的数据库密码';"
mysql -e "FLUSH PRIVILEGES;"

# 3. 安装Python环境
echo -e "${YELLOW}步骤3: 安装Python环境...${NC}"
apt install -y python3 python3-pip python3-venv python3-dev build-essential

# 4. 安装Node.js
echo -e "${YELLOW}步骤4: 安装Node.js...${NC}"
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# 5. 安装nginx
echo -e "${YELLOW}步骤5: 安装nginx...${NC}"
apt install -y nginx

# 6. 创建项目目录
echo -e "${YELLOW}步骤6: 创建项目目录...${NC}"
mkdir -p /root/project
cd /root/project

# 7. 下载项目（如果还没有的话）
if [ ! -d "ZhiQing" ]; then
    echo "项目目录不存在，请先上传项目文件到 /root/project/ZhiQing"
    echo "或者使用git克隆项目"
    exit 1
fi

cd ZhiQing

# 8. 创建数据库和表
echo -e "${YELLOW}步骤8: 创建数据库和表...${NC}"

# 创建数据库
echo "创建数据库..."
mysql -uroot -p您的数据库密码 -e "CREATE DATABASE IF NOT EXISTS zhiqing_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行统一的数据库创建脚本
echo "创建数据库表结构..."
if [ -f "ddl/create_database.sql" ]; then
    echo "使用统一的数据库创建脚本..."
    mysql -uroot -p您的数据库密码 zhiqing_db < ddl/create_database.sql
    echo "数据库表结构创建完成！"
else
    echo "警告: ddl/create_database.sql 不存在，尝试使用旧的DDL文件..."
    # 备用方案：使用旧的DDL文件
    for sql_file in ddl/create/20250521/*.sql; do
        if [ -f "$sql_file" ]; then
            echo "执行 $sql_file..."
            mysql -uroot -p您的数据库密码 zhiqing_db < "$sql_file"
        else
            echo "警告: $sql_file 不存在"
        fi
    done
fi

# 9. 部署后端
echo -e "${YELLOW}步骤9: 部署后端...${NC}"

# 创建Python虚拟环境
echo "创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建环境变量文件
echo "创建环境变量文件..."
cat > .env << 'ENVEOF'
MYSQL_DB=zhiqing_db
MYSQL_USER=root
MYSQL_PASSWORD=您的数据库密码
MYSQL_HOST=localhost
MYSQL_PORT=3306
DEBUG=False
SECRET_KEY=django-insecure-d@o%v)9%#12_8or1o#9h$d79i+dp@!+k5t6dg_r9b_rvgwnpiy
ENVEOF

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
echo "创建超级用户..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

# 10. 部署前端
echo -e "${YELLOW}步骤10: 部署前端...${NC}"
cd zhiqing_ui

# 安装前端依赖
echo "安装前端依赖..."
npm install

# 构建前端
echo "构建前端..."
npm run build

cd ..

# 11. 配置nginx
echo -e "${YELLOW}步骤11: 配置nginx...${NC}"

# 创建nginx配置文件
echo "创建nginx配置文件..."
cat > /etc/nginx/sites-available/zhiqing << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root /root/project/ZhiQing/zhiqing_ui/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    # 后端API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 媒体文件
    location /media/ {
        alias /root/project/ZhiQing/media/;
    }
}
NGINXEOF

# 启用站点
ln -sf /etc/nginx/sites-available/zhiqing /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试nginx配置
nginx -t

# 重启nginx
systemctl restart nginx

# 12. 创建后端服务
echo -e "${YELLOW}步骤12: 创建后端服务...${NC}"

# 创建systemd服务文件
echo "创建systemd服务文件..."
cat > /etc/systemd/system/zhiqing.service << 'SERVICEEOF'
[Unit]
Description=ZhiQing Django Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/project/ZhiQing
Environment=PATH=/root/project/ZhiQing/venv/bin
ExecStart=/root/project/ZhiQing/venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICEEOF

# 重新加载systemd配置
systemctl daemon-reload

# 启动服务
systemctl start zhiqing
systemctl enable zhiqing

# 13. 检查服务状态
echo -e "${YELLOW}步骤13: 检查服务状态...${NC}"
echo "检查MySQL状态..."
systemctl status mysql --no-pager -l

echo "检查nginx状态..."
systemctl status nginx --no-pager -l

echo "检查后端服务状态..."
systemctl status zhiqing --no-pager -l

echo "检查端口监听..."
netstat -tlnp | grep -E ':(80|8000|3306)' || echo "端口检查完成"

echo -e "${GREEN}=== 安装完成！ ===${NC}"
echo -e "${GREEN}前端访问地址: http://$(hostname -I | awk '{print $1}')${NC}"
echo -e "${GREEN}后端API地址: http://$(hostname -I | awk '{print $1}'):8000${NC}"
echo -e "${GREEN}数据库: MySQL (localhost:3306)${NC}"
echo -e "${GREEN}超级用户: admin / admin123${NC}"
echo -e "${YELLOW}请确保服务器防火墙开放了80端口${NC}"

# 显示服务管理命令
echo -e "${BLUE}=== 服务管理命令 ===${NC}"
echo "启动后端: systemctl start zhiqing"
echo "停止后端: systemctl stop zhiqing"
echo "重启后端: systemctl restart zhiqing"
echo "查看状态: systemctl status zhiqing"
echo "查看日志: journalctl -u zhiqing -f"
