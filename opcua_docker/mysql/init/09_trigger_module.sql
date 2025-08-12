/* stage3_done이 0→1로 바뀌는 순간 최근10 버퍼 갱신(밀어넣기 방식) */
USE secondary_battery_db;

DROP TRIGGER IF EXISTS trg_module_after_update;
DELIMITER $$
CREATE TRIGGER trg_module_after_update
AFTER UPDATE ON module
FOR EACH ROW
BEGIN
  IF NEW.stage3_done = 1 AND (OLD.stage3_done IS NULL OR OLD.stage3_done = 0) THEN
    -- 1) row_no 9→삭제, 0~8은 +1
    UPDATE module_last10
       SET row_no = row_no + 1
     WHERE row_no BETWEEN 0 AND 9
     ORDER BY row_no DESC;

    DELETE FROM module_last10 WHERE row_no > 9;

    -- 2) 최신 건을 row_no=0으로 삽입
    INSERT INTO module_last10
      (row_no, lot_no, module_type, v1_angle, v1_ok, v2_result, v2_ok,
       voltage, voltage_ok, stage1_done, stage2_done, stage3_done, created_at)
    VALUES
      (0, NEW.lot_no, NEW.module_type, NEW.v1_angle, NEW.v1_ok, NEW.v2_result, NEW.v2_ok,
       NEW.voltage, NEW.voltage_ok, NEW.stage1_done, NEW.stage2_done, NEW.stage3_done, NOW());
  END IF;
END$$
DELIMITER ;