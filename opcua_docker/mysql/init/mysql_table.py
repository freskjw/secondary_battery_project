"""
mysql_table.py
--------------
· config.env 에 정의된 DB 접속 정보를 읽어
  - lot_tracker
  - module_process_log
  두 테이블을 생성(존재 시 무시)하고 초기 레코드를 삽입한다.
"""

from __future__ import annotations

import os
import mysql.connector
from dotenv import load_dotenv


# ──────────────────────────────────────────────────────────────────────────
# 1. 환경 설정
# ──────────────────────────────────────────────────────────────────────────
load_dotenv("config.env")

DB_CONFIG = dict(
    host      = os.getenv("DB_HOST", "localhost"),
    port      = int(os.getenv("DB_PORT", 3306)),
    user      = os.getenv("DB_USER", "root"),
    password  = os.getenv("DB_PW"  , ""),
    database  = os.getenv("DB_NAME", "secondary_battery_db"),
)

# ──────────────────────────────────────────────────────────────────────────
# 2. 스키마 정의
# ──────────────────────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lot_tracker(
    module_type   VARCHAR(10)  PRIMARY KEY,
    last_serial   INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO lot_tracker (module_type, last_serial)
VALUES ('2x3', 0), ('2x4', 0);

CREATE TABLE IF NOT EXISTS module_process_log(
    lot_no               VARCHAR(20)  PRIMARY KEY,
    module_type          VARCHAR(10),
    angle                FLOAT,
    vision1_result       VARCHAR(20),
    vision1_timestamp    DATETIME,
    vision2_result       VARCHAR(20),
    vision2_timestamp    DATETIME,
    voltage              FLOAT,
    voltage_result       VARCHAR(10),
    voltage_timestamp    DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


# ──────────────────────────────────────────────────────────────────────────
# 3. 메인 루틴
# ──────────────────────────────────────────────────────────────────────────
def main() -> None:
    try:
        with mysql.connector.connect(**DB_CONFIG) as db, db.cursor() as cur:
            # 여러 개의 statement를 세미콜론 기준으로 분리 실행
            for stmt in SCHEMA_SQL.strip().split(";"):
                s = stmt.strip()
                if s:
                    cur.execute(s)
            db.commit()

        print("✅  테이블 생성·초기화 완료")

    except mysql.connector.Error as e:
        print("❌  MySQL Error:", e)


# ──────────────────────────────────────────────────────────────────────────
# 4. Entrypoint
# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()