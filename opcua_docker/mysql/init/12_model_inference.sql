USE secondary_battery_db;

-- 3) 모델/버전·신뢰도 추적(비전 품질 설명용)
CREATE TABLE IF NOT EXISTS model_registry (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  model_name VARCHAR(64) NOT NULL,
  version    VARCHAR(32) NOT NULL,
  trained_at TIMESTAMP NULL,
  notes VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_model (model_name, version)
);

CREATE TABLE IF NOT EXISTS module_inference (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  lot_no VARCHAR(24) NOT NULL,
  station ENUM('VISION1','VISION2') NOT NULL,
  model_name VARCHAR(64) NOT NULL,
  model_version VARCHAR(32) NOT NULL,
  confidence DECIMAL(6,3) NULL,      -- 최종 판정 신뢰도
  latency_ms INT NULL,               -- 응답지연(운영 지표)
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_inf_lot (lot_no, station, created_at),
  KEY idx_inf_model (model_name, model_version, created_at),
  CONSTRAINT fk_inf_module FOREIGN KEY (lot_no) REFERENCES module(lot_no) ON DELETE CASCADE
);