USE secondary_battery_db;


-- 1) 규격/목표치 테이블 (CP/CPK·판정 기준 단일 출처)
CREATE TABLE IF NOT EXISTS spec_limit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  module_type ENUM('6P','8P') NOT NULL,
  metric VARCHAR(32) NOT NULL,      -- 'voltage' 등
  lsl DECIMAL(12,5) NULL,
  usl DECIMAL(12,5) NULL,
  target DECIMAL(12,5) NULL,
  effective_from DATE NOT NULL,
  effective_to   DATE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_spec (module_type, metric, effective_from),
  KEY idx_spec_active (metric, effective_from, effective_to)
);

-- 기본 규격 시드 (전압: 7.70 ~ 8.30 V, 타깃 8.00 V)
INSERT INTO spec_limit(module_type, metric, lsl, usl, target, effective_from)
VALUES
 ('6P','voltage',7.70000,8.30000,8.00000, CURRENT_DATE()),
 ('8P','voltage',7.70000,8.30000,8.00000, CURRENT_DATE())
ON DUPLICATE KEY UPDATE lsl=VALUES(lsl), usl=VALUES(usl), target=VALUES(target);

-- 현재 유효 규격 뷰(조회 편의)
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