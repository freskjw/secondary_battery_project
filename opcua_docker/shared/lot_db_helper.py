"""
lot_db_helper.py  (rev.2025-07-31)  ─ DB-Queue 지원
─────────────────────────────────────────────────
* create_module_lot() : 모듈 LOT 발급 (SP 호출)
* update_module()     : 특정 LOT 행 컬럼 업데이트
* get_next_lot(stage) : 공정 단계별 “미처리 LOT” 1개 가져오기   ← 🆕
"""

from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Mapping, Any

from dotenv import load_dotenv
from mysql.connector import pooling, MySQLConnection
from mysql.connector.cursor import MySQLCursor

load_dotenv("config.env")

DB_CONFIG: Mapping[str, Any] = {
    "host": os.getenv("DB_HOST", "mysql"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root2"),
    "password": os.getenv("DB_PW", "projectteam2@"),
    "database": os.getenv("DB_NAME", "secondary_battery_db"),
    "charset": "utf8mb4",
    "autocommit": False,
}
POOL = pooling.MySQLConnectionPool(pool_name="LOT_POOL",
                                   pool_size=5,
                                   **DB_CONFIG)


@contextmanager
def get_conn_cursor() -> tuple[MySQLConnection, MySQLCursor]:
    conn = POOL.get_connection()
    cur = conn.cursor()
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ────────────────────────────────────────────────────────────
def create_module_lot(product_type: str) -> str:
    """새 모듈 LOT 발급 (SP 호출) → LOT 문자열 반환"""
    if product_type not in ("6P", "8P"):
        raise ValueError(product_type)

    with get_conn_cursor() as (_, cur):
        cur.callproc("sp_create_module", (product_type, ""))
        for res in cur.stored_results():
            return res.fetchone()[1]          # (None, 'KCM-6P-001')
    raise RuntimeError("sp_create_module failed")


def update_module(lot_no: str, **updates):
    """module 테이블 LOT 행 업데이트 (컬럼=값 …)"""
    if not updates:
        return
    sets = ", ".join(f"{k}=%s" for k in updates.keys())
    params = list(updates.values()) + [lot_no]
    with get_conn_cursor() as (_, cur):
        cur.execute(f"UPDATE module SET {sets} WHERE lot_no=%s", params)


# ────────────────────────────────────────────────────────────
def get_next_lot(stage: int) -> str | None:
    """
    stage-2 : Vision 2 가 처리할 LOT
       조건 → stage1_done=1 AND stage2_done=0
    stage-3 : Voltage 가 처리할 LOT
       조건 → stage2_done=1 AND stage3_done=0
    """
    if stage not in (2, 3):
        raise ValueError("stage must be 2 or 3")

    sql = (
        "SELECT lot_no FROM module "
        "WHERE {cond} ORDER BY created_at ASC LIMIT 1"
    )
    cond = ("stage1_done=1 AND stage2_done=0"
            if stage == 2
            else "stage2_done=1 AND stage3_done=0")

    with get_conn_cursor() as (_, cur):
        cur.execute(sql.format(cond=cond))
        row = cur.fetchone()
        return row[0] if row else None