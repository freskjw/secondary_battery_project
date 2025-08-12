-- 13_module_timestamps.sql (최종 교정본)
USE secondary_battery_db;

SET @db  := 'secondary_battery_db';
SET @tbl := 'module';

-- 공통 존재여부
SET @has_created := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND COLUMN_NAME='created_at');
SET @has_updated := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND COLUMN_NAME='updated_at');

-- ===== v1_time =====
SET @has_v1 := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND COLUMN_NAME='v1_time');
SET @pos_v1 := CASE
  WHEN @has_updated>0 THEN ' AFTER `updated_at`'
  WHEN @has_created>0 THEN ' AFTER `created_at`'
  ELSE ''
END;
SET @sql := IF(@has_v1=0,
  CONCAT('ALTER TABLE `',@tbl,'` ADD COLUMN `v1_time` TIMESTAMP NULL', @pos_v1),
  'SELECT 1'
);
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ===== v2_time =====
SET @has_v2 := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND COLUMN_NAME='v2_time');
SET @has_v1 := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND COLUMN_NAME='v1_time');
SET @pos_v2 := CASE
  WHEN @has_v1>0 THEN ' AFTER `v1_time`'
  WHEN @has_updated>0 THEN ' AFTER `updated_at`'
  WHEN @has_created>0 THEN ' AFTER `created_at`'
  ELSE ''
END;
SET @sql := IF(@has_v2=0,
  CONCAT('ALTER TABLE `',@tbl,'` ADD COLUMN `v2_time` TIMESTAMP NULL', @pos_v2),
  'SELECT 1'
);
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ===== voltage_time =====
SET @has_vt := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND COLUMN_NAME='voltage_time');
SET @has_v2 := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND COLUMN_NAME='v2_time');
SET @pos_vt := CASE
  WHEN @has_v2>0 THEN ' AFTER `v2_time`'
  WHEN @has_v1>0 THEN ' AFTER `v1_time`'
  WHEN @has_updated>0 THEN ' AFTER `updated_at`'
  WHEN @has_created>0 THEN ' AFTER `created_at`'
  ELSE ''
END;
SET @sql := IF(@has_vt=0,
  CONCAT('ALTER TABLE `',@tbl,'` ADD COLUMN `voltage_time` TIMESTAMP NULL', @pos_vt),
  'SELECT 1'
);
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ===== 인덱스 (없을 때만 생성) =====
SET @has_idx := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND INDEX_NAME='idx_module_v1_time');
SET @sql := IF(@has_idx=0, 'CREATE INDEX `idx_module_v1_time` ON `module`(`v1_time`)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_idx := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND INDEX_NAME='idx_module_v2_time');
SET @sql := IF(@has_idx=0, 'CREATE INDEX `idx_module_v2_time` ON `module`(`v2_time`)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_idx := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA=@db AND TABLE_NAME=@tbl AND INDEX_NAME='idx_module_voltage_time');
SET @sql := IF(@has_idx=0, 'CREATE INDEX `idx_module_voltage_time` ON `module`(`voltage_time`)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;