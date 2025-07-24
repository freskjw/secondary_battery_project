"""
lot_db_helper.py  (rev.2025-07-24)
──────────────────────────────────
* upsert_process_log → 새로운 스키마(line_id, process_id, measure_value, result)
"""

from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Mapping, Literal
from dotenv import load_dotenv
from mysql.connector import pooling, MySQLConnection
from mysql.connector.cursor import MySQLCursor

# ── 환경
load_dotenv("config.env")
DB_CONFIG: Mapping[str,str|int] = {
    "host":     os.getenv("DB_HOST","mysql"),
    "port":     int(os.getenv("DB_PORT",3306)),
    "user":     os.getenv("DB_USER","root2"),
    "password": os.getenv("DB_PW","projectteam2@"),
    "database": os.getenv("DB_NAME","secondary_battery_db"),
    "charset":  "utf8mb4",
    "autocommit": False,
}
POOL = pooling.MySQLConnectionPool(pool_name="LOT_POOL", pool_size=5, **DB_CONFIG)

@contextmanager
def get_conn_cursor() -> tuple[MySQLConnection, MySQLCursor]:
    conn = POOL.get_connection(); cur = conn.cursor()
    try:
        yield conn, cur; conn.commit()
    except:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

# ── LOT 시리얼 (기존 함수 그대로) ─────────────────────────
PREFIX_MAP = {"2x3":"6P","2x4":"8P"}
def _next_lot(cur:MySQLCursor, module_type:str)->str:
    if module_type not in PREFIX_MAP: raise ValueError(module_type)
    prefix = PREFIX_MAP[module_type]
    cur.execute("SELECT last_serial FROM lot_tracker WHERE module_type=%s FOR UPDATE",(module_type,))
    row = cur.fetchone()
    serial = 1 if row is None else row[0]+1
    if row is None:
        cur.execute("INSERT INTO lot_tracker(module_type,last_serial) VALUES(%s,%s)",(module_type,serial))
    else:
        cur.execute("UPDATE lot_tracker SET last_serial=%s WHERE module_type=%s",(serial,module_type))
    return f"KCM-{prefix}-{serial:03d}"

# ── 공정 로그 UPSERT (New) ────────────────────────────────
def upsert_process_log(
    lot:str,
    line_id:int,
    module_type:str,
    process_id:str,
    measure:float|None=None,
    result:str|None=None,
)->None:
    """module_process_log UPSERT"""
    with get_conn_cursor() as (_,cur):
        cur.execute(
            """INSERT IGNORE INTO module_process_log
                 (lot_no,line_id,module_type,process_id,created_at)
               VALUES (%s,%s,%s,%s,NOW())""",
            (lot,line_id,module_type,process_id)
        )
        sets, vals = [], []
        if measure is not None:
            sets.append("measure_value=%s"); vals.append(measure)
        if result:
            sets.append("result=%s");        vals.append(result)
        if sets:
            sql=f"UPDATE module_process_log SET {', '.join(sets)} WHERE lot_no=%s"
            cur.execute(sql, (*vals, lot))