USE secondary_battery_db;

-- 타입별 최근 전압 추세(그래프용, 최신 200)
CREATE OR REPLACE VIEW v_voltage_recent AS
SELECT lot_no, module_type, voltage, voltage_ok, created_at
FROM module
WHERE stage3_done=1
ORDER BY created_at DESC
LIMIT 200;

-- 팩 상세(팩-모듈 3개 피벗)
CREATE OR REPLACE VIEW v_pack_detail AS
WITH pm AS (
  SELECT
    pack_lot_no,
    module_lot_no,
    ROW_NUMBER() OVER (PARTITION BY pack_lot_no ORDER BY module_lot_no) AS rn
  FROM pack_module_map
)
SELECT
  p.pack_lot_no,
  p.pack_type,
  p.pack_voltage,
  p.completed_at,
  MAX(CASE WHEN pm.rn=1 THEN pm.module_lot_no END) AS mod1,
  MAX(CASE WHEN pm.rn=2 THEN pm.module_lot_no END) AS mod2,
  MAX(CASE WHEN pm.rn=3 THEN pm.module_lot_no END) AS mod3
FROM pack p
LEFT JOIN pm ON pm.pack_lot_no = p.pack_lot_no
GROUP BY p.pack_lot_no, p.pack_type, p.pack_voltage, p.completed_at;