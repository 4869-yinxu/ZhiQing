-- 为现有数据库添加 cancelled 状态
-- 执行前请备份数据库

-- 1. 检查当前状态枚举
SELECT COLUMN_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'document_upload_task' 
  AND COLUMN_NAME = 'status';

-- 2. 更新状态枚举，添加 cancelled 状态
ALTER TABLE `document_upload_task` 
MODIFY COLUMN `status` enum('pending','processing','completed','failed','cancelled') DEFAULT 'pending' COMMENT '任务状态';

-- 3. 验证更新结果
SELECT COLUMN_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'document_upload_task' 
  AND COLUMN_NAME = 'status';

-- 4. 查看当前任务状态分布
SELECT status, COUNT(*) as count 
FROM document_upload_task 
GROUP BY status;

-- 5. 可选：将一些长期处于 processing 状态的任务标记为 cancelled
-- UPDATE document_upload_task 
-- SET status = 'cancelled', 
--     error_message = '任务超时自动取消', 
--     updated_at = NOW() 
-- WHERE status = 'processing' 
--   AND updated_at < DATE_SUB(NOW(), INTERVAL 1 HOUR);
