/* 05_lot_sp.sql ─ LOT·Pack SP & Trigger */
DELIMITER $$

CREATE PROCEDURE sp_create_module(IN p_type ENUM('6P','8P'), OUT o_lot VARCHAR(20))
BEGIN
  DECLARE v_seq INT; DECLARE v_id BIGINT;
  SELECT next_seq INTO v_seq
    FROM lot_counter WHERE entity = CONCAT('module_',p_type) FOR UPDATE;
  UPDATE lot_counter SET next_seq = v_seq+1
    WHERE entity = CONCAT('module_',p_type);

  SET o_lot = CONCAT('KCM-',p_type,'-',LPAD(v_seq,3,'0'));
  SET v_id  = UNIX_TIMESTAMP(NOW(6))*1000 + FLOOR(RAND()*1000);

  INSERT INTO module(module_id,lot_no,product_type)
        VALUES (v_id, o_lot, p_type);
END$$


CREATE PROCEDURE sp_try_pack_build(IN p_module_id BIGINT)
BEGIN
  DECLARE v_type ENUM('6P','8P'); DECLARE v_cnt INT;
  SELECT product_type INTO v_type
    FROM module WHERE module_id=p_module_id AND pack_id IS NULL;
  IF v_type IS NULL THEN LEAVE proc; END IF;

  SELECT COUNT(*) INTO v_cnt
    FROM module WHERE product_type=v_type AND finished=1 AND pack_id IS NULL;
  IF v_cnt < 3 THEN LEAVE proc; END IF;

  /* Pack LOT 발급 */
  DECLARE v_seq INT; DECLARE v_pack BIGINT; DECLARE v_lot VARCHAR(20);
  SELECT next_seq INTO v_seq
    FROM lot_counter WHERE entity = CONCAT('pack_',v_type) FOR UPDATE;
  UPDATE lot_counter SET next_seq = v_seq+1
    WHERE entity = CONCAT('pack_',v_type);

  SET v_pack = UNIX_TIMESTAMP(NOW(6))*1000 + FLOOR(RAND()*1000);
  SET v_lot  = CONCAT('KCP-',v_type,'-',LPAD(v_seq,3,'0'));

  INSERT INTO pack(pack_id,lot_no,product_type,build_count,completed_at,
                   voltage_avg,capacity_theo)
    SELECT v_pack,v_lot,v_type,3,NOW(), AVG(voltage), 0
      FROM module
     WHERE product_type=v_type AND finished=1 AND pack_id IS NULL
     LIMIT 3;

  UPDATE module
     SET pack_id=v_pack, completed_at=NOW()
   WHERE product_type=v_type AND finished=1 AND pack_id IS NULL
   LIMIT 3;
END$$


CREATE TRIGGER trg_finish_stage3
AFTER UPDATE ON module
FOR EACH ROW
  IF NEW.stage3_done=1 AND NEW.finished=0 THEN
    UPDATE module SET finished=1 WHERE module_id = NEW.module_id;
    CALL sp_try_pack_build(NEW.module_id);
  END IF$$
DELIMITER ;