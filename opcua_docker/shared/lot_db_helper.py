"""
LOT / 공정이력 DB Helper
------------------------
MySQL(MariaDB) 연결 풀을 사용해 트랜잭션-단위로 LOT 번호를 발급하고
Vision · 전압 결과를 INSERT / UPDATE 합니다.

* .env / config.env 로 DB 접속 정보 주입
* SELECT … FOR UPDATE 로 LOT 중복 방지
* Connection Pool 로 컨테이너 다중-스레드 접근 최적화
"""

from __future__ import annotations

import os, datetime
from contextlib import contextmanager
from typing import Literal, Mapping

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling, MySQLConnection, Cursor

# 1. 환경 변수 로드
# ──────────────────────────────────────────────────────────────────────────
load_dotenv("config.env")

DB_CONFIG: Mapping[str, str | int] = dict(
    host        = os.getenv("DB_HOST", "mysql"),
    port        = int(os.getenv("DB_PORT", "3306")),
    user        = os.getenv("DB_USER", "root2"),
    password    = os.getenv("DB_PW",   "projectteam2@"),
    database    = os.getenv("DB_NAME", "secondary_battery_db"),
    charset     = "utf8mb4",
    autocommit  = False,  # 트랜잭션 수동 제어
)

# 2. 연결 풀 (5개 기본)
# ──────────────────────────────────────────────────────────────────────────
POOL = pooling.MySQLConnectionPool(
    pool_name         = os.getenv("DB_POOL_NAME",  "LOT_POOL"),
    pool_size         = int(os.getenv("DB_POOL_SIZE", "5")),
    pool_reset_session= True,
    **DB_CONFIG,
)

@contextmanager
def get_conn_cursor() -> tuple[MySQLConnection, Cursor]:
    """
    with 블록으로 (conn, cur) 제공 → 자동 commit / rollback / close
    """
    conn = POOL.get_connection()
    cur  = conn.cursor()
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
        
# 3. LOT 번호 발급
# ──────────────────────────────────────────────────────────────────────────
PREFIX_MAP: dict[str, str] = {
    "2x3": "6P",
    "2x4": "8P",
}


def _next_lot(cur: Cursor, module_type: str) -> str:
    """
    LOT 번호 생성 (행 잠금)
    - module_type ∈ {"2x3", "2x4"}
    - lot_tracker 테이블의 last_serial 컬럼을 1 증분
    """
    if module_type not in PREFIX_MAP:
        raise ValueError(f"지원하지 않는 module_type: {module_type}")

    prefix = PREFIX_MAP[module_type]

    # ① 현재 시리얼 LOCK & READ
    cur.execute(
        """
        SELECT last_serial
          FROM lot_tracker
         WHERE module_type = %s
           FOR UPDATE
        """,
        (module_type,),
    )
    row = cur.fetchone()
    if row is None:
        serial = 1
        cur.execute(
            "INSERT INTO lot_tracker (module_type, last_serial) VALUES (%s, %s)",
            (module_type, serial),
        )
    else:
        serial = row[0] + 1
        cur.execute(
            "UPDATE lot_tracker SET last_serial = %s WHERE module_type = %s",
            (serial, module_type),
        )

    return f"KCM-{prefix}-{serial:03d}"

# 4. Vision1 INSERT
# ──────────────────────────────────────────────────────────────────────────
def insert_vision1(
    module_type: Literal["2x3", "2x4"],
    angle: float,
    result: str,
) -> str:
    """
    Vision1 측정치 최초 기록
    * 새로운 LOT 번호 자동 발급
    * 이미 존재 시 angle / result / timestamp 갱신
    """
    with get_conn_cursor() as (conn, cur):
        lot = _next_lot(cur, module_type)

        cur.execute(
            """
            INSERT INTO module_process_log
                (lot_no, module_type, angle,
                 vision1_result, vision1_timestamp)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                 angle             = VALUES(angle),
                 vision1_result    = VALUES(vision1_result),
                 vision1_timestamp = NOW()
            """,
            (lot, module_type, angle, result),
        )
        return lot
    
# 5. Vision2 · 전압 UPDATE
# ──────────────────────────────────────────────────────────────────────────
def update_vision2(lot: str, result: str) -> None:
    with get_conn_cursor() as (conn, cur):
        cur.execute(
            """
            UPDATE module_process_log
               SET vision2_result    = %s,
                   vision2_timestamp = NOW()
             WHERE lot_no = %s
            """,
            (result, lot),
        )


def update_voltage(lot: str, volt: float, result: str) -> None:
    with get_conn_cursor() as (conn, cur):
        cur.execute(
            """
            UPDATE module_process_log
               SET voltage           = %s,
                   voltage_result    = %s,
                   voltage_timestamp = NOW()
             WHERE lot_no = %s
            """,
            (volt, result, lot),
        )