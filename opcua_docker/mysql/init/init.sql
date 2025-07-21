-- LOT 시리얼 관리 테이블
CREATE TABLE IF NOT EXISTS lot_tracker (
  module_type   VARCHAR(10) PRIMARY KEY,
  last_serial   INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 초기값 삽입 (중복 무시)
INSERT IGNORE INTO lot_tracker (module_type, last_serial)
VALUES ('2x3', 0), ('2x4', 0);

-- 모듈 공정 로그 테이블
CREATE TABLE IF NOT EXISTS module_process_log (
  lot_no             VARCHAR(20) PRIMARY KEY,
  module_type        VARCHAR(10),
  angle              FLOAT,
  vision1_result     VARCHAR(20),
  vision1_timestamp  DATETIME,
  vision2_result     VARCHAR(20),
  vision2_timestamp  DATETIME,
  voltage            FLOAT,
  voltage_result     VARCHAR(10),
  voltage_timestamp  DATETIME,
  FOREIGN KEY (module_type) REFERENCES lot_tracker(module_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- vision1 검사 결과 로그 테이블
CREATE TABLE IF NOT EXISTS vision1_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lot_no VARCHAR(50),
    module_type VARCHAR(10),
    angle FLOAT,
    angle_result VARCHAR(10),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- vision2 검사 결과 로그 테이블
CREATE TABLE IF NOT EXISTS vision2_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lot_no VARCHAR(50),
    module_type VARCHAR(10),
    vision2_result VARCHAR(10),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 전압 검사 결과 로그 테이블
CREATE TABLE IF NOT EXISTS voltage_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lot_no VARCHAR(50),
    module_type VARCHAR(10),
    voltage FLOAT,
    voltage_result VARCHAR(10),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);