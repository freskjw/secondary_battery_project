/* 05_create_pack.sql ─ Pack 정보 & Traceability */

-- 0) LOT 연속번호 관리
CREATE TABLE IF NOT EXISTS pack_tracker (
  pack_type   VARCHAR(10) PRIMARY KEY,   -- '6P','8P'
  last_serial INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT IGNORE INTO pack_tracker VALUES ('6P',0),('8P',0);

-- 1) Pack 헤더
CREATE TABLE IF NOT EXISTS pack (
  pack_lot_no  VARCHAR(20) PRIMARY KEY,      -- ex) KCP-6P-001
  pack_type    VARCHAR(10),                  -- '2x3','2x4'
  pack_voltage DECIMAL(10,3),
  pack_capacity DECIMAL(10,3),
  completed_at DATETIME(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Pack-Module 매핑 (추적성)
CREATE TABLE IF NOT EXISTS pack_module_map (
  pack_lot_no  VARCHAR(20),
  module_lot_no VARCHAR(20),
  PRIMARY KEY (pack_lot_no, module_lot_no),
  FOREIGN KEY (pack_lot_no)   REFERENCES pack(pack_lot_no),
  FOREIGN KEY (module_lot_no) REFERENCES module_process_log(lot_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3) module_process_log 에 pack_lot_no 컬럼 추가
ALTER TABLE module_process_log
  ADD COLUMN IF NOT EXISTS pack_lot_no VARCHAR(20) NULL;
