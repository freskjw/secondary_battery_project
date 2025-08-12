USE secondary_battery_db;

-- 2) 불량 코드 표준화 + 다중 불량 기록
CREATE TABLE IF NOT EXISTS defect_code (
  code VARCHAR(16) PRIMARY KEY,
  category ENUM('VOLT','VISION','OTHER') NOT NULL,
  source   ENUM('V1','V2','PLC','SYS') NOT NULL,
  severity ENUM('MINOR','MAJOR','CRITICAL') NOT NULL,
  description VARCHAR(255) NOT NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS module_defect (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  lot_no VARCHAR(24) NOT NULL,
  defect_code VARCHAR(16) NOT NULL,
  station ENUM('VISION1','VISION2','VOLT','PACK') NOT NULL,
  score DECIMAL(6,3) NULL,              -- 신뢰도/편차 등
  meta JSON NULL,                       -- bbox, 좌표, 스냅샷 경로 등
  detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_md_lot (lot_no, detected_at),
  KEY idx_md_code (defect_code, detected_at),
  CONSTRAINT fk_md_module FOREIGN KEY (lot_no) REFERENCES module(lot_no) ON DELETE CASCADE,
  CONSTRAINT fk_md_code   FOREIGN KEY (defect_code) REFERENCES defect_code(code)
);

-- 기본 불량 코드 시드
INSERT INTO defect_code(code, category, source, severity, description) VALUES
  ('VLOW','VOLT','PLC','MAJOR','Voltage below LSL'),
  ('VHIGH','VOLT','PLC','MAJOR','Voltage above USL'),
  ('VNG','VOLT','PLC','MAJOR','Voltage out of spec (generic)'),
  ('VIS_MISS','VISION','V1','CRITICAL','Missing cell detected'),
  ('VIS_ANGLE','VISION','V1','MAJOR','Angle out of tolerance'),
  ('VIS_ORIENT','VISION','V2','MAJOR','Orientation/assembly error'),
  ('OTHER_STATION','OTHER','SYS','MINOR','Other station issue')
ON DUPLICATE KEY UPDATE description=VALUES(description), severity=VALUES(severity), enabled=1;