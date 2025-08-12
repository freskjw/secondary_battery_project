USE secondary_battery_db;

-- 6) KPI 목표치/알람 정책(역할별 라우팅)
CREATE TABLE IF NOT EXISTS kpi_target (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  module_type ENUM('6P','8P') NOT NULL,
  metric VARCHAR(32) NOT NULL,         -- ok_rate, cpk, leadtime_v2 등
  target DECIMAL(12,5) NOT NULL,
  warn_threshold DECIMAL(12,5) NULL,   -- 경고 임계(예: OK률 0.95)
  crit_threshold DECIMAL(12,5) NULL,   -- 치명 임계(예: OK률 0.90)
  effective_from DATE NOT NULL,
  effective_to   DATE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_kpi (module_type, metric, effective_from)
);

CREATE TABLE IF NOT EXISTS alarm_policy (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  metric VARCHAR(32) NOT NULL,         -- ok_rate, cpk...
  severity ENUM('WARNING','CRITICAL') NOT NULL,
  audience ENUM('operator','lead','manager') NOT NULL,
  channel ENUM('telegram','email','webhook') NOT NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_alarm (metric, severity, audience, enabled)
);

-- KPI/알람 기본 시드 (예시값, 필요시 수정)
INSERT INTO kpi_target(module_type, metric, target, warn_threshold, crit_threshold, effective_from) VALUES
 ('6P','ok_rate',0.97000,0.95000,0.90000,CURRENT_DATE()),
 ('8P','ok_rate',0.97000,0.95000,0.90000,CURRENT_DATE()),
 ('6P','cpk',    1.33000,1.00000,0.67000,CURRENT_DATE()),
 ('8P','cpk',    1.33000,1.00000,0.67000,CURRENT_DATE())
ON DUPLICATE KEY UPDATE target=VALUES(target), warn_threshold=VALUES(warn_threshold), crit_threshold=VALUES(crit_threshold);

INSERT INTO alarm_policy(metric, severity, audience, channel) VALUES
 ('ok_rate','WARNING','operator','telegram'),
 ('ok_rate','CRITICAL','lead','telegram'),
 ('cpk',    'CRITICAL','manager','email')
ON DUPLICATE KEY UPDATE channel=VALUES(channel), enabled=1;