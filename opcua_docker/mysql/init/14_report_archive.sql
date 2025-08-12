USE secondary_battery_db;

-- 5) 리포트 보관/재현성(아카이브)
CREATE TABLE IF NOT EXISTS report_archive (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  report_date DATE NOT NULL,
  period ENUM('D','W','M') NOT NULL,
  audience ENUM('operator','lead','manager') NOT NULL,
  json_payload MEDIUMTEXT NOT NULL,    -- 집계 원자료(JSON)
  html MEDIUMTEXT NULL,
  text_summary TEXT NULL,
  prompt_version VARCHAR(32) NOT NULL,
  hash VARCHAR(64) NOT NULL,           -- report_date+audience+prompt_version 해시
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_report (report_date, period, audience, prompt_version)
);