# v6 ★ PATCHED (lazy pool + retry + self-heal)
from __future__ import annotations
import os, time
from contextlib import contextmanager
from typing import Mapping, Any
from dotenv import load_dotenv
from mysql.connector import pooling, MySQLConnection, errors
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

_POOL: pooling.MySQLConnectionPool | None = None
_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))

def _get_pool() -> pooling.MySQLConnectionPool:
    """Create pool lazily with retries; reuse on success."""
    global _POOL
    if _POOL is not None:
        return _POOL
    last_err = None
    for i in range(60):  # ~2분 대기
        try:
            _POOL = pooling.MySQLConnectionPool(
                pool_name="LOT_POOL", pool_size=_POOL_SIZE, **DB_CONFIG
            )
            return _POOL
        except errors.Error as e:
            last_err = e
            print(f"[lot_db_helper] waiting mysql pool... ({i+1}/60) {e}")
            time.sleep(2)
    raise RuntimeError(f"MySQL pool not ready: {last_err}")

@contextmanager
def get_conn_cursor() -> tuple[MySQLConnection, MySQLCursor]:
    global _POOL
    pool = _get_pool()
    try:
        conn = pool.get_connection()
    except errors.Error:
        # pool broken → reset and recreate once
        _POOL = None
        conn = _get_pool().get_connection()
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

# 이하 보조 함수들은 그대로 사용
def _type_to_db(product_type: str) -> str:
    if product_type == "6P": return "2x3"
    if product_type == "8P": return "2x4"
    raise ValueError(product_type)

def _db_to_label(db_type: str) -> str:
    if db_type == "2x3": return "6P"
    if db_type == "2x4": return "8P"
    raise ValueError(db_type)

# create_module_lot / update_module / get_next_lot 그대로


def create_module_lot(product_type: str) -> str:
    """LOT 발급: KCM-{6P|8P}-{001..}; module.module_type은 '2x3'/'2x4'"""
    if product_type not in ("6P", "8P"):
        raise ValueError(product_type)
    db_type = _type_to_db(product_type)
    prefix  = f"KCM-{product_type}-"
    with get_conn_cursor() as (_, cur):
        cur.execute("""
            SELECT COALESCE(MAX(CAST(SUBSTRING_INDEX(lot_no,'-',-1) AS UNSIGNED)),0)
              FROM module
             WHERE module_type=%s
        """, (db_type,))
        maxn = int(cur.fetchone()[0] or 0)
        lot_no = f"{prefix}{maxn+1:03d}"
        cur.execute("""
            INSERT INTO module
              (lot_no, module_type, stage1_done, stage2_done, stage3_done)
            VALUES (%s, %s, 0, 0, 0)
        """, (lot_no, db_type))
        return lot_no

def update_module(lot_no: str, **updates):
    """module 테이블 특정 LOT 행 업데이트"""
    if not updates:
        return
    sets = ", ".join(f"{k}=%s" for k in updates.keys())
    params = list(updates.values()) + [lot_no]
    with get_conn_cursor() as (_, cur):
        cur.execute(f"UPDATE module SET {sets} WHERE lot_no=%s", params)

def get_next_lot(stage: int) -> str | None:
    """
    v6: 스크랩 제외
    stage-2 : stage1_done=1 AND stage2_done=0 AND is_scrap=0
    stage-3 : stage2_done=1 AND stage3_done=0 AND is_scrap=0
    """
    if stage not in (2, 3):
        raise ValueError("stage must be 2 or 3")
    cond = ("stage1_done=1 AND stage2_done=0 AND is_scrap=0" if stage == 2
            else "stage2_done=1 AND stage3_done=0 AND is_scrap=0")
    sql = ("SELECT lot_no FROM module "
           f"WHERE {cond} ORDER BY created_at ASC LIMIT 1")
    with get_conn_cursor() as (_, cur):
        cur.execute(sql)
        row = cur.fetchone()
        return row[0] if row else None