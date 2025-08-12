/* v6 ★ PATCHED: 스크랩 플래그/사유 추가 */
USE secondary_battery_db;

CREATE TABLE IF NOT EXISTS module (
  lot_no        VARCHAR(20) PRIMARY KEY,
  module_type   VARCHAR(10),        -- '2x3'/'2x4'
  v1_angle      DECIMAL(6,2)   NULL,
  v1_ok         TINYINT        NULL,
  v2_result     VARCHAR(32)    NULL,
  v2_ok         TINYINT        NULL,
  voltage       DECIMAL(10,3)  NULL,
  voltage_ok    TINYINT        NULL,
  is_scrap      TINYINT DEFAULT 0,  -- ★
  scrap_stage   CHAR(3) NULL,       -- ★ 'P02' 등
  scrap_reason  VARCHAR(32) NULL,   -- ★ 'Misinsert'/'Missing'/...
  scrap_at      DATETIME NULL,      -- ★
  stage1_done   TINYINT DEFAULT 0,
  stage2_done   TINYINT DEFAULT 0,
  stage3_done   TINYINT DEFAULT 0,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_module_stage2 ON module (stage1_done, stage2_done, is_scrap);
CREATE INDEX idx_module_stage3 ON module (stage2_done, stage3_done, is_scrap);
CREATE INDEX idx_module_ok     ON module (v1_ok, v2_ok, voltage_ok, is_scrap);