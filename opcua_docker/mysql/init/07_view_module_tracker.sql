/* 07_view_module_tracker.sql (fixed) */
CREATE OR REPLACE VIEW vw_module_tracker AS
SELECT
  ROW_NUMBER() OVER (ORDER BY created_at DESC)       AS No ,
  lot_no                   AS `LOT No`,
  module_type              AS Type,
  IFNULL(CAST(v1_angle AS CHAR),'...')               AS Angle,
  IFNULL(v2_result,'...')                            AS `Vision-2`,
  IFNULL(CAST(voltage  AS CHAR),'...')               AS Voltage,
  IFNULL(DATE_FORMAT(completed_at,'%H:%i:%s'),'...') AS Time,
  stage3_done                                          AS _done
FROM module_tracker
ORDER BY created_at DESC
LIMIT 10;