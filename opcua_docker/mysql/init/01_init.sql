/* 01_init.sql ─ DB 초기 스키마 (rev.2025-07-24)
   ▸ availability_rate 오타 수정
   ▸ line_run / process_production / line_summary 추가
   ▸ legacy lot_tracker · module_process_log 보완          */

-- 1) 공정 마스터
CREATE TABLE IF NOT EXISTS process_master (
  process_id   CHAR(3) PRIMARY KEY,
  step_order   TINYINT,
  process_name VARCHAR(100),
  description  TEXT,
  target_uph   DECIMAL(6,2) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) 라인 가동(세션)
CREATE TABLE IF NOT EXISTS line_run (
  line_id       INT AUTO_INCREMENT PRIMARY KEY,
  work_date     DATE,
  target_output INT,
  target_uph    DECIMAL(6,2) NULL,
  start_dt      DATETIME(3),
  end_dt        DATETIME(3),
  line_state    ENUM('RUNNING','COMPLETE','ABORTED')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3) LOT 시리얼
CREATE TABLE IF NOT EXISTS lot_tracker (
  module_type VARCHAR(10) PRIMARY KEY,
  last_serial INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO lot_tracker (module_type, last_serial)
VALUES ('2x3',0),('2x4',0);

-- 4) 모듈 공정 로그
CREATE TABLE IF NOT EXISTS module_process_log (
  lot_no        VARCHAR(20) PRIMARY KEY,
  line_id       INT,
  module_type   VARCHAR(10),
  process_id    CHAR(3),
  measure_value DECIMAL(10,3),
  result        VARCHAR(10),
  created_at    DATETIME,
  FOREIGN KEY (line_id) REFERENCES line_run(line_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5) process_production
CREATE TABLE IF NOT EXISTS process_production (
  record_id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  line_id              INT,
  process_id           CHAR(3),
  uph                  DECIMAL(6,2),
  daily_output         INT,
  defect               INT,
  defect_rate          DECIMAL(5,2),
  quality_rate         DECIMAL(5,2),
  availability_rate    DECIMAL(5,2),          -- ✔ 오타 수정
  planne_downtime      INT,
  unplanned_downtime   INT,
  start_dt             DATETIME(3),
  end_dt               DATETIME(3),
  defect_breakdown_json JSON,
  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_pp_line (line_id),
  FOREIGN KEY (line_id) REFERENCES line_run(line_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6) line_summary
CREATE TABLE IF NOT EXISTS line_summary (
  summary_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  line_id             INT,
  work_date           DATE,
  total_output        INT,
  total_defect        INT,
  global_quality_rate DECIMAL(5,2),
  plan_down           INT,
  unplan_down         INT,
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (line_id) REFERENCES line_run(line_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;