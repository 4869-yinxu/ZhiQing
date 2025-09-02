-- =====================================================
-- ZhiQing 知识库管理系统 - 数据库创建脚本
-- 版本: 2025-08-30
-- 描述: 完整的数据库表结构创建脚本
-- =====================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `zhiqing_db` 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `zhiqing_db`;

-- =====================================================
-- 1. 基础用户管理表
-- =====================================================

-- 角色表
CREATE TABLE `role` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '角色名称',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_bin COMMENT '角色描述',
  `permissions` json DEFAULT NULL COMMENT '权限配置JSON',
  `status` tinyint DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='角色表';

-- 用户表
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `real_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `role_id` int NOT NULL,
  `status` tinyint DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `last_login_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_role_id` (`role_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_user_role` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='用户表';

-- =====================================================
-- 2. AI模型配置表
-- =====================================================

-- 大模型服务商表
CREATE TABLE `llmprovider` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '服务商名称',
  `code` varchar(50) NOT NULL COMMENT '服务商标识',
  `desc` text COMMENT '描述',
  `user_id` int NOT NULL DEFAULT '1' COMMENT '所属用户ID',
  `username` varchar(100) DEFAULT NULL COMMENT '创建人姓名',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_public` tinyint(1) DEFAULT '0' COMMENT '是否为公共服务商 0-私有 1-公共',
  `created_by` int DEFAULT NULL COMMENT '创建者用户ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_code` (`user_id`,`code`),
  UNIQUE KEY `uk_user_name` (`user_id`,`name`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_code` (`code`),
  KEY `idx_name` (`name`),
  KEY `idx_llm_provider_public_created` (`is_public`,`created_by`),
  CONSTRAINT `fk_llmprovider_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='大模型服务商';

-- 大模型配置表
CREATE TABLE `llmmodel` (
  `id` int NOT NULL AUTO_INCREMENT,
  `provider_id` int NOT NULL COMMENT '所属服务商ID',
  `name` varchar(100) NOT NULL COMMENT '模型名称',
  `model_type` varchar(100) NOT NULL COMMENT '模型类型',
  `api_key` varchar(200) NOT NULL COMMENT 'API Key',
  `base_url` varchar(200) DEFAULT NULL COMMENT 'Base URL',
  `max_tokens` int DEFAULT '4096' COMMENT '最大Token数',
  `temperature` float DEFAULT '0.7' COMMENT '温度参数',
  `is_default` tinyint(1) DEFAULT '0' COMMENT '是否默认',
  `user_id` int NOT NULL DEFAULT '1' COMMENT '所属用户ID',
  `username` varchar(100) DEFAULT NULL COMMENT '创建人姓名',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_public` tinyint(1) DEFAULT '0' COMMENT '是否为公共模型 0-私有 1-公共',
  `created_by` int DEFAULT NULL COMMENT '创建者用户ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_model_user_id` (`user_id`),
  KEY `idx_llm_model_public_created` (`is_public`,`created_by`),
  CONSTRAINT `fk_llmmodel_provider` FOREIGN KEY (`provider_id`) REFERENCES `llmprovider` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_llmmodel_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='大模型配置';

-- 嵌入模型配置表
CREATE TABLE `embedding_model` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(100) NOT NULL COMMENT '模型显示名称',
  `model_type` varchar(50) NOT NULL COMMENT '模型类型：openai, zhipu, baidu, dashscope, xunfei, tencent, sentence_transformers, ollama',
  `api_type` varchar(20) NOT NULL COMMENT 'API类型：online, local',
  `api_key` varchar(500) DEFAULT NULL COMMENT 'API密钥（仅在线模型需要）',
  `api_url` varchar(500) DEFAULT NULL COMMENT 'API地址（预设，用户一般不需要修改）',
  `model_name` varchar(100) NOT NULL COMMENT '具体模型名称（如text-embedding-ada-002或BAAI/bge-large-zh-v1.5）',
  `local_path` varchar(500) DEFAULT NULL COMMENT '本地模型路径（可选，为空则自动下载到缓存）',
  `vector_dimension` int NOT NULL COMMENT '向量维度（由模型决定，不可修改）',
  `max_tokens` int NOT NULL COMMENT '最大token数（由模型决定，不可修改）',
  `batch_size` int DEFAULT '32' COMMENT '推荐批处理大小（可调整）',
  `timeout` int DEFAULT '30' COMMENT '请求超时时间（秒）',
  `is_default` tinyint(1) DEFAULT '0' COMMENT '是否为默认模型',
  `is_public` tinyint(1) DEFAULT '1' COMMENT '是否为公共模型（预设模型都是公共的）',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否启用',
  `is_preset` tinyint(1) DEFAULT '0' COMMENT '是否为系统预设模型（预设模型不允许删除）',
  `user_id` int NOT NULL COMMENT '创建用户ID',
  `username` varchar(50) NOT NULL COMMENT '创建用户名',
  `description` text COMMENT '模型描述',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_model_type` (`model_type`),
  KEY `idx_api_type` (`api_type`),
  KEY `idx_is_default` (`is_default`),
  KEY `idx_is_preset` (`is_preset`),
  CONSTRAINT `fk_embedding_model_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='嵌入模型配置表';

-- =====================================================
-- 3. 知识库管理表
-- =====================================================

-- 知识库表
CREATE TABLE `knowledge_database` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '知识库名称',
  `description` text COMMENT '知识库描述',
  `embedding_model_id` int DEFAULT NULL COMMENT '嵌入模型ID',
  `vector_dimension` int NOT NULL DEFAULT '384' COMMENT '向量维度',
  `index_type` varchar(50) NOT NULL COMMENT '索引类型',
  `doc_count` int NOT NULL DEFAULT '0' COMMENT '文档数量',
  `user_id` int NOT NULL COMMENT '创建人ID',
  `username` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_name` (`user_id`,`name`),
  KEY `idx_creator` (`user_id`),
  KEY `idx_embedding_model_id` (`embedding_model_id`),
  CONSTRAINT `fk_knowledge_database_embedding_model` FOREIGN KEY (`embedding_model_id`) REFERENCES `embedding_model` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_knowledge_database_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识库表';

-- 知识文档表
CREATE TABLE `knowledge_document` (
  `id` int NOT NULL AUTO_INCREMENT,
  `database_id` int NOT NULL COMMENT '所属知识库ID',
  `filename` varchar(255) NOT NULL COMMENT '文件名称',
  `file_path` varchar(500) NOT NULL COMMENT '文件存储路径',
  `file_type` varchar(50) NOT NULL COMMENT '文件类型',
  `file_size` bigint NOT NULL COMMENT '文件大小(字节)',
  `chunking_method` varchar(50) NOT NULL COMMENT '分块方法',
  `chunk_size` int NOT NULL COMMENT '分块大小',
  `similarity_threshold` decimal(3,2) DEFAULT '0.70' COMMENT '语义分块相似度阈值',
  `overlap_size` int DEFAULT '100' COMMENT '递归分块重叠大小',
  `chunk_count` int NOT NULL COMMENT '分块数量',
  `user_id` int NOT NULL COMMENT '上传用户ID',
  `username` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '上传用户名',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_database_id` (`database_id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `fk_document_database` FOREIGN KEY (`database_id`) REFERENCES `knowledge_database` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_document_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识文档表';

-- 知识文档分块表
CREATE TABLE `knowledge_document_chunk` (
  `id` int NOT NULL AUTO_INCREMENT,
  `document_id` int NOT NULL COMMENT '所属文档ID',
  `database_id` int NOT NULL COMMENT '所属知识库ID',
  `chunk_index` int NOT NULL COMMENT '分块索引',
  `content` text NOT NULL COMMENT '分块内容',
  `vector_id` varchar(64) DEFAULT NULL COMMENT '向量ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_document_id` (`document_id`),
  KEY `idx_database_id` (`database_id`),
  CONSTRAINT `fk_chunk_database` FOREIGN KEY (`database_id`) REFERENCES `knowledge_database` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chunk_document` FOREIGN KEY (`document_id`) REFERENCES `knowledge_document` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识文档分块表';

-- =====================================================
-- 4. 文档处理任务表
-- =====================================================

-- 文档上传任务表
CREATE TABLE `document_upload_task` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` varchar(64) NOT NULL COMMENT '任务唯一标识',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `database_id` bigint(20) NOT NULL COMMENT '知识库ID',
  `filename` varchar(255) NOT NULL COMMENT '文件名',
  `file_path` varchar(500) NOT NULL COMMENT '文件路径',
  `file_size` bigint(20) NOT NULL COMMENT '文件大小(字节)',
  `chunking_method` varchar(20) DEFAULT 'token' COMMENT '分块方法',
  `chunk_size` int(11) DEFAULT 500 COMMENT '分块大小',
  `similarity_threshold` decimal(3,2) DEFAULT 0.70 COMMENT '相似度阈值',
  `overlap_size` int(11) DEFAULT 100 COMMENT '重叠大小',
  `custom_delimiter` varchar(10) DEFAULT '\n\n' COMMENT '自定义分隔符',
  `window_size` int(11) DEFAULT 3 COMMENT '滑动窗口大小',
  `step_size` int(11) DEFAULT 1 COMMENT '步长',
  `min_chunk_size` int(11) DEFAULT 50 COMMENT '最小分块大小',
  `max_chunk_size` int(11) DEFAULT 2000 COMMENT '最大分块大小',
  `status` enum('pending','processing','completed','failed','cancelled') DEFAULT 'pending' COMMENT '任务状态',
  `progress` int(11) DEFAULT 0 COMMENT '处理进度(0-100)',
  `error_message` text COMMENT '错误信息',
  `chunk_count` int(11) DEFAULT 0 COMMENT '生成的分块数量',
  `document_id` bigint(20) DEFAULT NULL COMMENT '生成的文档ID',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `started_at` timestamp NULL DEFAULT NULL COMMENT '开始处理时间',
  `completed_at` timestamp NULL DEFAULT NULL COMMENT '完成时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_database_id` (`database_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_upload_task_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_upload_task_database` FOREIGN KEY (`database_id`) REFERENCES `knowledge_database` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档上传任务表';

-- =====================================================
-- 5. 聊天对话表
-- =====================================================

-- 聊天对话表
CREATE TABLE `chat_conversation` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL COMMENT '对话标题',
  `knowledge_base_id` int NOT NULL COMMENT '知识库ID',
  `knowledge_base_name` varchar(100) NOT NULL COMMENT '知识库名称',
  `model_id` int NOT NULL COMMENT '模型ID',
  `model_name` varchar(100) NOT NULL COMMENT '模型名称',
  `user_id` int DEFAULT NULL COMMENT '用户ID',
  `username` varchar(50) DEFAULT NULL COMMENT '用户名',
  `message_count` int DEFAULT '0' COMMENT '消息数量',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_kb_id` (`knowledge_base_id`),
  KEY `idx_model_id` (`model_id`),
  KEY `idx_conversation_user_id` (`user_id`),
  CONSTRAINT `fk_conversation_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_conversation_kb` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_database` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_conversation_model` FOREIGN KEY (`model_id`) REFERENCES `llmmodel` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='聊天对话表';

-- 聊天消息表
CREATE TABLE `chat_message` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conversation_id` int NOT NULL COMMENT '对话ID',
  `user_id` int NOT NULL DEFAULT '1' COMMENT '所属用户ID',
  `role` varchar(20) NOT NULL COMMENT '角色(user/assistant)',
  `content` text NOT NULL COMMENT '消息内容',
  `citations` json DEFAULT NULL COMMENT '引用来源',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_conversation_id` (`conversation_id`),
  KEY `idx_message_user_id` (`user_id`),
  CONSTRAINT `fk_chat_message_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `chat_conversation` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chat_message_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='聊天消息表';

-- =====================================================
-- 6. 文本过滤表
-- =====================================================

-- 敏感词过滤管理表
CREATE TABLE `sensitive_words` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `word` varchar(100) NOT NULL COMMENT '敏感词',
  `level` enum('low','medium','high') NOT NULL DEFAULT 'medium' COMMENT '敏感级别：low-低，medium-中，high-高',
  `replacement` varchar(100) NOT NULL DEFAULT '***' COMMENT '替换词',
  `category` enum('general','political','business','technical','personal','other') NOT NULL DEFAULT 'general' COMMENT '分类：general-通用，political-政治，business-商业，technical-技术，personal-个人隐私，other-其他',
  `description` text COMMENT '描述信息',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用：1-启用，0-禁用',
  `priority` int(11) NOT NULL DEFAULT 0 COMMENT '优先级：数值越大优先级越高',
  `created_by` bigint(20) COMMENT '创建人ID',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` bigint(20) COMMENT '更新人ID',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_word` (`word`),
  KEY `idx_level` (`level`),
  KEY `idx_category` (`category`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_priority` (`priority`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_sensitive_words_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_sensitive_words_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='敏感词过滤管理表';

-- 停用词库管理表
CREATE TABLE `stop_words` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `word` varchar(100) NOT NULL COMMENT '停用词',
  `language` enum('chinese','english','mixed') NOT NULL DEFAULT 'chinese' COMMENT '语言类型：chinese-中文，english-英文，mixed-混合',
  `category` enum('general','technical','academic','business','medical','legal','other') NOT NULL DEFAULT 'general' COMMENT '分类：general-通用，technical-技术，academic-学术，business-商业，medical-医疗，legal-法律，other-其他',
  `description` text COMMENT '描述信息',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用：1-启用，0-禁用',
  `priority` int(11) NOT NULL DEFAULT 0 COMMENT '优先级：数值越大优先级越高',
  `created_by` bigint(20) COMMENT '创建人ID',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` bigint(20) COMMENT '更新人ID',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_word_language` (`word`, `language`),
  KEY `idx_language` (`language`),
  KEY `idx_category` (`category`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_priority` (`priority`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_stop_words_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_stop_words_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='停用词库管理表';

-- =====================================================
-- 7. 初始化基础数据
-- =====================================================

-- 插入默认角色
INSERT INTO `role` (`name`, `description`, `permissions`, `status`) VALUES
('超级管理员', '系统超级管理员，拥有所有权限', '{"all": true}', 1),
('管理员', '系统管理员，拥有大部分权限', '{"user_manage": true, "kb_manage": true, "system_manage": true}', 1),
('普通用户', '普通用户，拥有基本权限', '{"kb_view": true, "chat": true}', 1);

-- 插入默认用户（密码：admin123）
INSERT INTO `user` (`username`, `password`, `email`, `real_name`, `role_id`, `status`) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uO.G', 'admin@zhiqing.com', '系统管理员', 1, 1);

-- 插入默认嵌入模型
INSERT INTO `embedding_model` (`name`, `model_type`, `api_type`, `model_name`, `vector_dimension`, `max_tokens`, `is_default`, `is_preset`, `user_id`, `username`, `description`) VALUES
('BGE-Large-ZH-V1.5', 'sentence_transformers', 'local', 'BAAI/bge-large-zh-v1.5', 1024, 512, 1, 1, 1, 'admin', '智源研究院开源的BGE大模型中文版本，支持中英文双语，在中文语义相似度计算和文本向量检索方面表现优异');

-- 插入默认LLM服务商
INSERT INTO `llmprovider` (`name`, `code`, `desc`, `user_id`, `username`, `is_public`, `created_by`) VALUES
('OpenAI', 'openai', 'OpenAI官方服务商', 1, 'admin', 1, 1),
('智谱AI', 'zhipu', '智谱AI服务商', 1, 'admin', 1, 1),
('百度文心', 'baidu', '百度文心一言服务商', 1, 'admin', 1, 1);

-- =====================================================
-- 脚本执行完成
-- =====================================================

SELECT 'ZhiQing 数据库创建完成！' AS message;
SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'zhiqing_db';
