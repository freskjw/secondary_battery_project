/* 최근 10 행만 보관하는 물리 테이블 (0~9 직접 관리) */

USE secondary_battery_db;

CREATE TABLE IF NOT EXISTS module_last10 (
  row_no       TINYINT UNSIGNED PRIMARY KEY,   -- 0..9
  lot_no       VARCHAR(20),
  module_type  VARCHAR(10),
  v1_angle     DECIMAL(6,2),
  v1_ok        TINYINT,
  v2_result    VARCHAR(20),
  v2_ok        TINYINT,
  voltage      DECIMAL(10,3),
  voltage_ok   TINYINT,
  stage1_done  TINYINT,
  stage2_done  TINYINT,
  stage3_done  TINYINT,
  created_at   DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;