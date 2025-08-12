/* v6 */
USE secondary_battery_db;

CREATE TABLE IF NOT EXISTS pack_tracker (
  pack_type   VARCHAR(10) PRIMARY KEY,   -- '6P','8P'
  last_serial INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT IGNORE INTO pack_tracker VALUES ('6P',0),('8P',0);

CREATE TABLE IF NOT EXISTS pack (
  pack_lot_no   VARCHAR(20) PRIMARY KEY,      -- ex) KCP-6P-001
  pack_type     VARCHAR(10),                  -- '2x3','2x4'
  pack_voltage  DECIMAL(10,3),
  pack_capacity DECIMAL(10,3),
  completed_at  DATETIME(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pack_module_map (
  pack_lot_no   VARCHAR(20),
  module_lot_no VARCHAR(20),
  PRIMARY KEY (pack_lot_no, module_lot_no),
  FOREIGN KEY (pack_lot_no)   REFERENCES pack(pack_lot_no),
  FOREIGN KEY (module_lot_no) REFERENCES module_process_log(lot_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;