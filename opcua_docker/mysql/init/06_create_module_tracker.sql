/* 06_create_module_tracker.sql (fixed) */
CREATE TABLE IF NOT EXISTS module_tracker (      -- ← 이름 변경
  lot_no       VARCHAR(20)  PRIMARY KEY,
  module_type  VARCHAR(10),
  v1_angle     DECIMAL(5,1)  NULL,
  v1_ok        TINYINT       DEFAULT 0,
  v2_result    VARCHAR(20)   NULL,
  voltage      DECIMAL(10,3) NULL,
  voltage_ok   TINYINT       DEFAULT 0,
  created_at   DATETIME      DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME      NULL,
  stage1_done  TINYINT       DEFAULT 0,
  stage2_done  TINYINT       DEFAULT 0,
  stage3_done  TINYINT       DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;