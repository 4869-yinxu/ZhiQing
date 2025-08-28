#!/bin/bash

# 数据库配置
DB_NAME="zhiqing_db"
DB_USER="root"
DB_PASS="1C231?@ncv"

# 创建数据库
mysql -u$DB_USER -p"$DB_PASS" -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"

# 执行所有DDL脚本
for sql_file in /Users/a4869/project/ZhiQing/ddl/create/20250521/*.sql; do
    echo "Executing $sql_file..."
    mysql -u$DB_USER -p"$DB_PASS" $DB_NAME < "$sql_file"
done

echo "Database $DB_NAME created successfully with all tables."