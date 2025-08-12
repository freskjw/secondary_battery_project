/* 16a_dummy_seed_schema.sql
   - dummy-seeder가 참조하는 전체 스키마 일괄 생성
   - next_lot() 함수 생성(1418 에러 방지용 설정 포함)
*/
CREATE DATABASE IF NOT EXISTS secondary_battery_dummy_db;
USE secondary_battery_dummy_db;

/* ------------------------------------------------------------------
   공통: 존재해도 에러 없도록 IF NOT EXISTS + InnoDB + utf8mb4
-------------------------------------------------------------------*/

/* 시퀀스 테이블 (lot 번호 생성용) */
CREATE TABLE IF NOT EXISTS lot_seq (
  prefix  VARCHAR(32) PRIMARY KEY,
  yymmdd  CHAR(6) NOT NULL,
  seq     INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 불량코드 마스터 (dummy-seeder가 INSERT 하는 컬럼 전부 포함) */
CREATE TABLE IF NOT EXISTS defect_code (
  code        VARCHAR(32) PRIMARY KEY,
  category    VARCHAR(16) NOT NULL,        -- 'VOLT','VISION','OTHER' 등
  source      VARCHAR(16) NOT NULL,        -- 'PLC','V1','V2','SYS' 등
  severity    ENUM('MINOR','MAJOR','CRITICAL') NOT NULL,
  description VARCHAR(255) NULL,
  enabled     TINYINT(1) NOT NULL DEFAULT 1,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 모듈(셀) 데이터 */
CREATE TABLE IF NOT EXISTS module (
  lot_no           VARCHAR(64) PRIMARY KEY,
  module_type      VARCHAR(8) NOT NULL,        -- '6P', '8P' 등
  angle            DECIMAL(6,2) NULL,
  angle_result     ENUM('OK','NG') NULL,
  vision1_result   ENUM('OK','NG') NULL,
  vision2_result   ENUM('OK','NG') NULL,
  voltage          DECIMAL(10,3) NULL,
  voltage_result   ENUM('OK','NG') NULL,
  stage            VARCHAR(16) NOT NULL DEFAULT 'DONE',
  created_at       DATETIME(3) NULL,
  updated_at       DATETIME(3) NULL,
  KEY idx_module_type_created (module_type, created_at),
  KEY idx_stage_created (stage, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 모듈 불량 이력 */
CREATE TABLE IF NOT EXISTS module_defect (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  lot_no       VARCHAR(64) NOT NULL,
  defect_code  VARCHAR(32) NOT NULL,
  station      VARCHAR(16) NULL,          -- 'VOLT','VISION1','VISION2' 등
  score        DECIMAL(10,3) NULL,
  meta         JSON NULL,
  detected_at  DATETIME(3) NULL,
  KEY idx_md_lot (lot_no),
  KEY idx_md_code (defect_code),
  CONSTRAINT fk_md_module
    FOREIGN KEY (lot_no) REFERENCES module(lot_no)
      ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_md_code
    FOREIGN KEY (defect_code) REFERENCES defect_code(code)
      ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 팩 헤더 */
CREATE TABLE IF NOT EXISTS pack (
  pack_no      VARCHAR(64) PRIMARY KEY,
  module_type  VARCHAR(8) NOT NULL,
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 팩-모듈 매핑 */
CREATE TABLE IF NOT EXISTS pack_module (
  pack_no  VARCHAR(64) NOT NULL,
  lot_no   VARCHAR(64) NOT NULL,
  PRIMARY KEY (pack_no, lot_no),
  KEY idx_pm_lot (lot_no),
  CONSTRAINT fk_pm_pack
    FOREIGN KEY (pack_no) REFERENCES pack(pack_no)
      ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_pm_module
    FOREIGN KEY (lot_no) REFERENCES module(lot_no)
      ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 공정능력(시더가 집계해 넣는 테이블) */
CREATE TABLE IF NOT EXISTS process_capability (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  module_type  VARCHAR(8) NOT NULL,
  window_size  INT NOT NULL,
  mean_v       DECIMAL(12,6) NOT NULL,
  std_v        DECIMAL(12,6) NOT NULL,
  cp           DECIMAL(12,6) NOT NULL,
  cpk          DECIMAL(12,6) NOT NULL,
  lsl          DECIMAL(12,6) NOT NULL,
  usl          DECIMAL(12,6) NOT NULL,
  computed_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_pc_type_time (module_type, computed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* ------------------------------------------------------------------
   함수 생성 (binlog 환경에서 1418 방지: trust_function_creators 임시 ON)
-------------------------------------------------------------------*/
SET @OLD_LOG_BIN_TRUST := @@GLOBAL.log_bin_trust_function_creators;
SET GLOBAL log_bin_trust_function_creators = 1;

DROP FUNCTION IF EXISTS next_lot;

DELIMITER $$
CREATE FUNCTION next_lot(p_prefix VARCHAR(32))
RETURNS VARCHAR(64)
NOT DETERMINISTIC
MODIFIES SQL DATA
BEGIN
  DECLARE today CHAR(6);
  DECLARE n INT;

  -- 서울 시간 기준 날짜(YYMMDD)
  SET today = DATE_FORMAT(CONVERT_TZ(NOW(),'UTC','Asia/Seoul'), '%y%m%d');

  -- prefix 별로 일자 바뀌면 seq 리셋, 아니면 +1
  INSERT INTO lot_seq(prefix, yymmdd, seq)
  VALUES(p_prefix, today, 1)
  ON DUPLICATE KEY UPDATE
    seq   = IF(yymmdd = VALUES(yymmdd), seq + 1, 1),
    yymmdd= VALUES(yymmdd);

  SELECT seq INTO n FROM lot_seq WHERE prefix = p_prefix;

  RETURN CONCAT(p_prefix, '-', today, '-', LPAD(n, 3, '0'));
END$$
DELIMITER ;

SET GLOBAL log_bin_trust_function_creators = IFNULL(@OLD_LOG_BIN_TRUST, 0);

/* 끝 */
