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