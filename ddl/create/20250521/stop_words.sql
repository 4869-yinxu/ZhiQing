-- 停用词库管理表
CREATE TABLE IF NOT EXISTS `stop_words` (
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
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='停用词库管理表';
