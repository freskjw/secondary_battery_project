-- 16_pack_summary.sql (FK 제거 버전)
USE secondary_battery_db;

CREATE TABLE IF NOT EXISTS pack_summary (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  pack_no VARCHAR(64) NULL,           -- FK 없이 참조키만 들고 있게
  modules INT NOT NULL DEFAULT 0,
  good INT NOT NULL DEFAULT 0,
  bad INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_pack_no (pack_no),
  KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;