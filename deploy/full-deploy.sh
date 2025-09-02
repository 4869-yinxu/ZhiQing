#!/bin/bash

# 完整部署脚本 - 适用于新服务器部署
# 包括：安装MySQL、创建数据库、部署后端、部署前端
#
# ⚠️ 重要：使用前请修改脚本开头的服务器配置信息
# SERVER_IP="您的服务器IP地址"
# SERVER_USER="您的服务器用户名"
# SERVER_PASS="您的服务器密码"
# SERVER_PORT="您的服务器SSH端口"

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 服务器信息 - 请根据实际情况修改
SERVER_IP="您的服务器IP地址"
SERVER_USER="您的服务器用户名"
SERVER_PASS="您的服务器密码"
SERVER_PORT="您的服务器SSH端口"
PROJECT_NAME="ZhiQing"

echo -e "${BLUE}=== 开始部署 $PROJECT_NAME 到服务器 $SERVER_IP ===${NC}"

# 1. 连接到服务器并安装MySQL
echo -e "${YELLOW}步骤1: 连接到服务器并安装MySQL...${NC}"

ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'EOF'
# 更新系统包
echo "更新系统包..."
apt update -y

# 安装MySQL服务器
echo "安装MySQL服务器..."
apt install -y mysql-server

# 启动MySQL服务
systemctl start mysql
systemctl enable mysql

# 设置MySQL root密码（使用环境变量中的密码）
echo "设置MySQL root密码..."
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$SERVER_PASS';"
mysql -e "FLUSH PRIVILEGES;"

# 创建项目目录
echo "创建项目目录..."
mkdir -p /root/project
cd /root/project

# 安装Python和pip
echo "安装Python和pip..."
apt install -y python3 python3-pip python3-venv

# 安装Node.js和npm
echo "安装Node.js和npm..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# 安装nginx
echo "安装nginx..."
apt install -y nginx

# 安装git
echo "安装git..."
apt install -y git

echo "基础环境安装完成！"
EOF

# 2. 上传项目文件
echo -e "${YELLOW}步骤2: 上传项目文件...${NC}"
scp -P $SERVER_PORT -r . $SERVER_USER@$SERVER_IP:/root/project/$PROJECT_NAME

# 3. 在服务器上创建数据库和表
echo -e "${YELLOW}步骤3: 创建数据库和表...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'EOF'
cd /root/project/ZhiQing

# 创建数据库
echo "创建数据库..."
mysql -uroot -p$SERVER_PASS -e "CREATE DATABASE IF NOT EXISTS zhiqing_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行统一的数据库创建脚本
echo "创建数据库表结构..."
if [ -f "ddl/create_database.sql" ]; then
    echo "使用统一的数据库创建脚本..."
    mysql -uroot -p$SERVER_PASS zhiqing_db < ddl/create_database.sql
    echo "数据库表结构创建完成！"
else
    echo "警告: ddl/create_database.sql 不存在，尝试使用旧的DDL文件..."
    # 备用方案：使用旧的DDL文件
    for sql_file in ddl/create/20250521/*.sql; do
        if [ -f "$sql_file" ]; then
            echo "执行 $sql_file..."
            mysql -uroot -p$SERVER_PASS zhiqing_db < "$sql_file"
        else
            echo "警告: $sql_file 不存在"
        fi
    done
fi
EOF

# 4. 部署后端
echo -e "${YELLOW}步骤4: 部署后端...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'EOF'
cd /root/project/ZhiQing

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
MYSQL_PASSWORD=$SERVER_PASS
MYSQL_HOST=localhost
MYSQL_PORT=3306
DEBUG=False
SECRET_KEY=django-insecure-d@o%v)9%#12_8or1o#9h$d79i+dp@!+k5t6dg_r9b_rvgwnpiy
ENVEOF

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py makemigrations
python manage.py migrate

# 创建超级用户（可选）
echo "创建超级用户..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

echo "后端部署完成！"
EOF

# 5. 部署前端
echo -e "${YELLOW}步骤5: 部署前端...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'EOF'
cd /root/project/ZhiQing/zhiqing_ui

# 安装前端依赖
echo "安装前端依赖..."
npm install

# 构建前端
echo "构建前端..."
npm run build

echo "前端构建完成！"
EOF

# 6. 配置nginx
echo -e "${YELLOW}步骤6: 配置nginx...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'EOF'
cd /root/project/ZhiQing

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

echo "nginx配置完成！"
EOF

# 7. 启动后端服务
echo -e "${YELLOW}步骤7: 启动后端服务...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'EOF'
cd /root/project/ZhiQing

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

echo "后端服务启动完成！"
EOF

# 8. 检查服务状态
echo -e "${YELLOW}步骤8: 检查服务状态...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'EOF'
echo "检查MySQL状态..."
systemctl status mysql --no-pager -l

echo "检查nginx状态..."
systemctl status nginx --no-pager -l

echo "检查后端服务状态..."
systemctl status zhiqing --no-pager -l

echo "检查端口监听..."
netstat -tlnp | grep -E ':(80|8000|3306)'
EOF

echo -e "${GREEN}=== 部署完成！ ===${NC}"
echo -e "${GREEN}前端访问地址: http://$SERVER_IP${NC}"
echo -e "${GREEN}后端API地址: http://$SERVER_IP:8000${NC}"
echo -e "${GREEN}数据库: MySQL (localhost:3306)${NC}"
echo -e "${GREEN}超级用户: admin / admin123${NC}"
echo -e "${YELLOW}请确保服务器防火墙开放了80端口${NC}"
