-- 33_report_archive_patch.sql (SAFE / idempotent / no AFTER)
-- 목적: report_archive 테이블에 json_payload, audience, lang 컬럼을 안전하게 보강
-- 대상 DB: secondary_battery_db, secondary_battery_dummy_db

SET NAMES utf8mb4;
SET sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ZERO_DATE,NO_ENGINE_SUBSTITUTION';

-- ───────────────────────────────────────────────────────────────────
-- 공용 함수처럼 두 번 반복 실행: @DB = 본 DB → 더미 DB
-- ───────────────────────────────────────────────────────────────────

-- 1) 본 DB
SET @DB := 'secondary_battery_db';

-- 테이블 존재 확인
SET @has_tab := (
  SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema=@DB AND table_name='report_archive'
);

-- json_payload
SET @exists := IF(@has_tab>0,
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@DB AND table_name='report_archive' AND column_name='json_payload'),
  1);
SET @sql := IF(@has_tab>0 AND @exists=0,
  CONCAT('ALTER TABLE `', @DB, '`.report_archive ADD COLUMN json_payload JSON NULL'),
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- audience
SET @exists := IF(@has_tab>0,
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@DB AND table_name='report_archive' AND column_name='audience'),
  1);
SET @sql := IF(@has_tab>0 AND @exists=0,
  CONCAT('ALTER TABLE `', @DB, '`.report_archive ADD COLUMN audience ENUM(''ALL'',''ENG'',''MGR'') NOT NULL DEFAULT ''ALL'''),
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- lang
SET @exists := IF(@has_tab>0,
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@DB AND table_name='report_archive' AND column_name='lang'),
  1);
SET @sql := IF(@has_tab>0 AND @exists=0,
  CONCAT('ALTER TABLE `', @DB, '`.report_archive ADD COLUMN lang VARCHAR(5) NOT NULL DEFAULT ''ko'''),
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- 2) 더미 DB
SET @DB := 'secondary_battery_dummy_db';

-- 테이블 존재 확인
SET @has_tab := (
  SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema=@DB AND table_name='report_archive'
);

-- json_payload
SET @exists := IF(@has_tab>0,
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@DB AND table_name='report_archive' AND column_name='json_payload'),
  1);
SET @sql := IF(@has_tab>0 AND @exists=0,
  CONCAT('ALTER TABLE `', @DB, '`.report_archive ADD COLUMN json_payload JSON NULL'),
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- audience
SET @exists := IF(@has_tab>0,
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@DB AND table_name='report_archive' AND column_name='audience'),
  1);
SET @sql := IF(@has_tab>0 AND @exists=0,
  CONCAT('ALTER TABLE `', @DB, '`.report_archive ADD COLUMN audience ENUM(''ALL'',''ENG'',''MGR'') NOT NULL DEFAULT ''ALL'''),
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- lang
SET @exists := IF(@has_tab>0,
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@DB AND table_name='report_archive' AND column_name='lang'),
  1);
SET @sql := IF(@has_tab>0 AND @exists=0,
  CONCAT('ALTER TABLE `', @DB, '`.report_archive ADD COLUMN lang VARCHAR(5) NOT NULL DEFAULT ''ko'''),
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SELECT 1;