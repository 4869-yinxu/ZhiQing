-- 为document_upload_task表添加status_message字段
-- 用于存储任务处理过程中的详细状态信息

ALTER TABLE `document_upload_task` 
ADD COLUMN `status_message` TEXT NULL COMMENT '任务状态消息' 
AFTER `error_message`;

-- 验证字段是否添加成功
DESCRIBE `document_upload_task`;
