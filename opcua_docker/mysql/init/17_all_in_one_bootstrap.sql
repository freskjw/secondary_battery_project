-- 17_all_in_one_bootstrap.sql
-- v6.x 호환 컬럼/인덱스/필드 보강 (주 DB + 더미 DB 모두 대상)
-- 안전 모드: 테이블 존재 여부/컬럼 존재 여부 확인 후에만 ALTER 수행

-- ===== 공용 유틸 프로시저 =====
DELIMITER //

DROP PROCEDURE IF EXISTS _addcol //
CREATE PROCEDURE _addcol(
    IN dbName   VARCHAR(64),
    IN tblName  VARCHAR(64),
    IN colName  VARCHAR(64),
    IN colDef   TEXT,
    IN afterCol VARCHAR(64)
)
BEGIN
  -- 테이블이 실제 BASE TABLE인지 확인 (VIEW 등 회피)
  IF EXISTS (
      SELECT 1 FROM information_schema.tables
       WHERE table_schema = dbName
         AND table_name   = tblName
         AND table_type   = 'BASE TABLE'
  ) THEN
    -- 컬럼이 없을 때만 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = dbName
           AND table_name   = tblName
           AND column_name  = colName
    ) THEN
      SET @sql = CONCAT(
        'ALTER TABLE `', dbName, '`.`', tblName, '` ',
        'ADD COLUMN `', colName, '` ', colDef
      );
      IF afterCol IS NOT NULL AND afterCol <> '' THEN
        SET @sql = CONCAT(@sql, ' AFTER `', afterCol, '`');
      END IF;
      PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
    END IF;
  END IF;
END //
 
DROP PROCEDURE IF EXISTS _addidx //
CREATE PROCEDURE _addidx(
    IN dbName  VARCHAR(64),
    IN tblName VARCHAR(64),
    IN idxName VARCHAR(64),
    IN idxCols TEXT
)
BEGIN
  IF EXISTS (
      SELECT 1 FROM information_schema.tables
       WHERE table_schema = dbName
         AND table_name   = tblName
         AND table_type   = 'BASE TABLE'
  ) THEN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
         WHERE table_schema = dbName
           AND table_name   = tblName
           AND index_name   = idxName
    ) THEN
      SET @sql = CONCAT(
        'ALTER TABLE `', dbName, '`.`', tblName, '` ',
        'ADD INDEX `', idxName, '` (', idxCols, ')'
      );
      PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
    END IF;
  END IF;
END //

DELIMITER ;

-- ===== 보강 타깃 DB 목록 =====
SET @DB_MAIN  = 'secondary_battery_db';
SET @DB_DUMMY = 'secondary_battery_dummy_db';

-- ===== module 테이블: v6 호환 컬럼 추가 (두 DB 공통) =====
--   writers/reporter에서 참조하는 컬럼들을 넉넉한 타입으로 맞춰둠
CALL _addcol(@DB_MAIN , 'module', 'lot_no'         , 'VARCHAR(64) NULL'                          , NULL);
CALL _addcol(@DB_MAIN , 'module', 'module_type'    , 'VARCHAR(10) NULL'                           , 'lot_no');
CALL _addcol(@DB_MAIN , 'module', 'v1_time'        , 'TIMESTAMP NULL'                             , 'module_type');
CALL _addcol(@DB_MAIN , 'module', 'v1_angle'       , 'DECIMAL(6,2) NULL'                          , 'v1_time');
CALL _addcol(@DB_MAIN , 'module', 'vision1_result' , "ENUM('OK','NG') NULL"                        , 'v1_angle');
CALL _addcol(@DB_MAIN , 'module', 'v2_time'        , 'TIMESTAMP NULL'                             , 'vision1_result');
CALL _addcol(@DB_MAIN , 'module', 'v2_gap'         , 'DECIMAL(6,2) NULL'                          , 'v2_time');
CALL _addcol(@DB_MAIN , 'module', 'vision2_result' , "ENUM('OK','NG') NULL"                        , 'v2_gap');
CALL _addcol(@DB_MAIN , 'module', 'voltage_time'   , 'TIMESTAMP NULL'                             , 'vision2_result');
CALL _addcol(@DB_MAIN , 'module', 'voltage_value'  , 'DECIMAL(10,3) NULL'                         , 'voltage_time');
CALL _addcol(@DB_MAIN , 'module', 'voltage_result' , "ENUM('OK','NG') NULL"                        , 'voltage_value');
CALL _addcol(@DB_MAIN , 'module', 'pack_lot_no'    , 'VARCHAR(64) NULL'                           , 'voltage_result');
CALL _addcol(@DB_MAIN , 'module', 'created_at'     , 'DATETIME(3) NULL'                           , 'pack_lot_no');
CALL _addcol(@DB_MAIN , 'module', 'updated_at'     , 'DATETIME NULL'                              , 'created_at');

CALL _addidx(@DB_MAIN, 'module', 'idx_module_lot_no', '`lot_no`');
CALL _addidx(@DB_MAIN, 'module', 'idx_module_v1_time', '`v1_time`');
CALL _addidx(@DB_MAIN, 'module', 'idx_module_v2_time', '`v2_time`');

CALL _addcol(@DB_DUMMY, 'module', 'lot_no'         , 'VARCHAR(64) NULL'                          , NULL);
CALL _addcol(@DB_DUMMY, 'module', 'module_type'    , 'VARCHAR(10) NULL'                           , 'lot_no');
CALL _addcol(@DB_DUMMY, 'module', 'v1_time'        , 'TIMESTAMP NULL'                             , 'module_type');
CALL _addcol(@DB_DUMMY, 'module', 'v1_angle'       , 'DECIMAL(6,2) NULL'                          , 'v1_time');
CALL _addcol(@DB_DUMMY, 'module', 'vision1_result' , "ENUM('OK','NG') NULL"                        , 'v1_angle');
CALL _addcol(@DB_DUMMY, 'module', 'v2_time'        , 'TIMESTAMP NULL'                             , 'vision1_result');
CALL _addcol(@DB_DUMMY, 'module', 'v2_gap'         , 'DECIMAL(6,2) NULL'                          , 'v2_time');
CALL _addcol(@DB_DUMMY, 'module', 'vision2_result' , "ENUM('OK','NG') NULL"                        , 'v2_gap');
CALL _addcol(@DB_DUMMY, 'module', 'voltage_time'   , 'TIMESTAMP NULL'                             , 'vision2_result');
CALL _addcol(@DB_DUMMY, 'module', 'voltage_value'  , 'DECIMAL(10,3) NULL'                         , 'voltage_time');
CALL _addcol(@DB_DUMMY, 'module', 'voltage_result' , "ENUM('OK','NG') NULL"                        , 'voltage_value');
CALL _addcol(@DB_DUMMY, 'module', 'pack_lot_no'    , 'VARCHAR(64) NULL'                           , 'voltage_result');
CALL _addcol(@DB_DUMMY, 'module', 'created_at'     , 'DATETIME(3) NULL'                           , 'pack_lot_no');
CALL _addcol(@DB_DUMMY, 'module', 'updated_at'     , 'DATETIME NULL'                              , 'created_at');

CALL _addidx(@DB_DUMMY, 'module', 'idx_module_lot_no', '`lot_no`');
CALL _addidx(@DB_DUMMY, 'module', 'idx_module_v1_time', '`v1_time`');
CALL _addidx(@DB_DUMMY, 'module', 'idx_module_v2_time', '`v2_time`');

-- ===== pack 테이블: created_at 필드 보강 (리포터에서 기간 집계 용) =====
CALL _addcol(@DB_MAIN , 'pack', 'created_at', 'DATETIME NULL', NULL);
CALL _addidx(@DB_MAIN , 'pack', 'idx_pack_created_at', '`created_at`');
CALL _addcol(@DB_DUMMY, 'pack', 'created_at', 'DATETIME NULL', NULL);
CALL _addidx(@DB_DUMMY, 'pack', 'idx_pack_created_at', '`created_at`');

-- ===== process_capability: 리포터에서 참조하는 통계 컬럼 보강 =====
CALL _addcol(@DB_MAIN , 'process_capability', 'lsl'         , 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_MAIN , 'process_capability', 'usl'         , 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_MAIN , 'process_capability', 'target'      , 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_MAIN , 'process_capability', 'computed_at' , 'DATETIME NULL'     , NULL);

CALL _addcol(@DB_DUMMY, 'process_capability', 'lsl'         , 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_DUMMY, 'process_capability', 'usl'         , 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_DUMMY, 'process_capability', 'target'      , 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_DUMMY, 'process_capability', 'computed_at' , 'DATETIME NULL'     , NULL);

-- ===== report_archive: json_payload 보강 (리포트 원본 저장) =====
CALL _addcol(@DB_MAIN , 'report_archive', 'json_payload', 'JSON NULL', NULL);
CALL _addcol(@DB_DUMMY, 'report_archive', 'json_payload', 'JSON NULL', NULL);

-- ===== kpi_target: 임계치 컬럼 보강 (있을 때만) =====
CALL _addcol(@DB_MAIN , 'kpi_target', 'target'        , 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_MAIN , 'kpi_target', 'warn_threshold', 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_MAIN , 'kpi_target', 'crit_threshold', 'DECIMAL(10,3) NULL', NULL);

CALL _addcol(@DB_DUMMY, 'kpi_target', 'target'        , 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_DUMMY, 'kpi_target', 'warn_threshold', 'DECIMAL(10,3) NULL', NULL);
CALL _addcol(@DB_DUMMY, 'kpi_target', 'crit_threshold', 'DECIMAL(10,3) NULL', NULL);

-- ===== 정리: 프로시저 정리(선택) =====
DROP PROCEDURE IF EXISTS _addcol;
DROP PROCEDURE IF EXISTS _addidx;