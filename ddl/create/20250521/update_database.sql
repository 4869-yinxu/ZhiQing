-- 更新数据库结构
-- 1. 为 document_upload_task 表添加 cancelled 状态

-- 检查当前状态枚举
SELECT COLUMN_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'document_upload_task' 
  AND COLUMN_NAME = 'status';

-- 更新状态枚举，添加 cancelled 状态
ALTER TABLE `document_upload_task` 
MODIFY COLUMN `status` enum('pending','processing','completed','failed','cancelled') DEFAULT 'pending' COMMENT '任务状态';

-- 验证更新结果
SELECT COLUMN_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'document_upload_task' 
  AND COLUMN_NAME = 'status';

-- 2. 查看当前任务状态分布
SELECT status, COUNT(*) as count 
FROM document_upload_task 
GROUP BY status;

-- 3. 查看用户表结构
DESCRIBE user;

-- 4. 查看角色表
SELECT * FROM role;
