-- 敏感词过滤管理表
CREATE TABLE IF NOT EXISTS `sensitive_words` (
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
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='敏感词过滤管理表';
