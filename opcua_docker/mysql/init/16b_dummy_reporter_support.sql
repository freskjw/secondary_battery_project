/* 16b_dummy_reporter_support.sql
   - 더미 DB에 리포터 필수 객체 생성: kpi_target, spec_limit(+vw), report_archive
*/
CREATE DATABASE IF NOT EXISTS secondary_battery_dummy_db;
USE secondary_battery_dummy_db;

-- KPI 목표/임계치
CREATE TABLE IF NOT EXISTS kpi_target (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  module_type ENUM('6P','8P') NOT NULL,
  metric VARCHAR(32) NOT NULL,
  target DECIMAL(12,5) NOT NULL,
  warn_threshold DECIMAL(12,5) NULL,
  crit_threshold DECIMAL(12,5) NULL,
  effective_from DATE NOT NULL,
  effective_to   DATE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_kpi (module_type, metric, effective_from)
);

INSERT INTO kpi_target(module_type, metric, target, warn_threshold, crit_threshold, effective_from) VALUES
 ('6P','ok_rate',0.97000,0.95000,0.90000,CURRENT_DATE()),
 ('8P','ok_rate',0.97000,0.95000,0.90000,CURRENT_DATE()),
 ('6P','cpk',    1.33000,1.00000,0.67000,CURRENT_DATE()),
 ('8P','cpk',    1.33000,1.00000,0.67000,CURRENT_DATE())
ON DUPLICATE KEY UPDATE target=VALUES(target), warn_threshold=VALUES(warn_threshold), crit_threshold=VALUES(crit_threshold);

-- 규격(표시용) + 활성 뷰
CREATE TABLE IF NOT EXISTS spec_limit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  module_type ENUM('6P','8P') NOT NULL,
  metric VARCHAR(32) NOT NULL,
  lsl DECIMAL(12,5) NULL,
  usl DECIMAL(12,5) NULL,
  target DECIMAL(12,5) NULL,
  effective_from DATE NOT NULL,
  effective_to   DATE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_spec (module_type, metric, effective_from),
  KEY idx_spec_active (metric, effective_from, effective_to)
);

INSERT INTO spec_limit(module_type, metric, lsl, usl, target, effective_from) VALUES
 ('6P','voltage',7.70000,8.30000,8.00000,CURRENT_DATE()),
 ('8P','voltage',7.70000,8.30000,8.00000,CURRENT_DATE())
ON DUPLICATE KEY UPDATE lsl=VALUES(lsl), usl=VALUES(usl), target=VALUES(target);

CREATE OR REPLACE VIEW vw_spec_active AS
SELECT s.*
FROM spec_limit s
JOIN (
  SELECT module_type, metric, MAX(effective_from) AS eff
  FROM spec_limit
  WHERE effective_from <= CURRENT_DATE()
    AND (effective_to IS NULL OR effective_to >= CURRENT_DATE())
  GROUP BY module_type, metric
) x ON x.module_type=s.module_type AND x.metric=s.metric AND x.eff=s.effective_from
WHERE (s.effective_to IS NULL OR s.effective_to >= CURRENT_DATE());

-- 리포트 아카이브
CREATE TABLE IF NOT EXISTS report_archive (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  report_date DATE NOT NULL,
  period ENUM('D','W','M') NOT NULL,
  audience ENUM('operator','lead','manager') NOT NULL,
  json_payload JSON NULL,
  html MEDIUMTEXT NULL,
  text_summary TEXT NULL,
  prompt_version VARCHAR(32) NOT NULL,
  hash VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_report (report_date, period, audience, prompt_version)
);
