USE secondary_battery_db;

DROP TABLE IF EXISTS process_capability;
DROP VIEW  IF EXISTS process_capability;

CREATE VIEW process_capability AS
    SELECT * FROM process_capability_2x3
    UNION ALL
    SELECT * FROM process_capability_2x4;