-- 04_create_capability (자동 실행용)
CREATE OR REPLACE VIEW process_capability AS
  SELECT * FROM process_capability_2x3
  UNION ALL
  SELECT * FROM process_capability_2x4;
