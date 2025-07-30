/* 04_create_capability.sql  ─ 테이블·뷰 충돌 방지 */
-- ❶ process_capability 라는 이름이 이미 TABLE 로 존재할 수도 있으므로 삭제
DROP TABLE IF EXISTS process_capability;
-- ❷ 혹시 이전에 VIEW 로 있다면 그것도 삭제
DROP VIEW  IF EXISTS process_capability;

-- ❸ 다시 VIEW 생성
CREATE VIEW process_capability AS
    SELECT * FROM process_capability_2x3
    UNION ALL
    SELECT * FROM process_capability_2x4;