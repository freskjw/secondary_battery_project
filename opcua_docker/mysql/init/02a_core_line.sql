/* v6.2 core line tables */
USE secondary_battery_db;

CREATE TABLE IF NOT EXISTS process_master (
  process_id   CHAR(3) PRIMARY KEY,
  step_order   TINYINT,
  process_name VARCHAR(100),
  description  TEXT,
  target_uph   DECIMAL(6,2) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS line_run (
  line_id       INT AUTO_INCREMENT PRIMARY KEY,
  work_date     DATE,
  target_output INT,
  target_uph    DECIMAL(6,2) NULL,
  start_dt      DATETIME(3),
  end_dt        DATETIME(3),
  line_state    ENUM('RUNNING','COMPLETE','ABORTED')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS module_process_log (
  lot_no        VARCHAR(20) PRIMARY KEY,
  line_id       INT,
  module_type   VARCHAR(10),         -- '2x3' / '2x4'
  process_id    CHAR(3),
  measure_value DECIMAL(10,3),
  result        VARCHAR(10),
  pack_lot_no   VARCHAR(20) NULL,
  created_at    DATETIME,
  FOREIGN KEY (line_id) REFERENCES line_run(line_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS process_production (
  record_id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  line_id               INT,
  process_id            CHAR(3),
  uph                   DECIMAL(6,2),
  daily_output          INT,
  defect                INT,
  defect_rate           DECIMAL(5,2),
  quality_rate          DECIMAL(5,2),
  availability_rate     DECIMAL(5,2),
  planned_downtime      INT,
  unplanned_downtime    INT,
  start_dt              DATETIME(3),
  end_dt                DATETIME(3),
  defect_breakdown_json JSON,
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_pp_line (line_id),
  FOREIGN KEY (line_id) REFERENCES line_run(line_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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