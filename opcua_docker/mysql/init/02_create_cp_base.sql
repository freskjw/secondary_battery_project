CREATE TABLE IF NOT EXISTS process_capability (
  calc_time   DATETIME PRIMARY KEY,
  module_type VARCHAR(10),
  cp_voltage  FLOAT,
  cpk_voltage FLOAT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;