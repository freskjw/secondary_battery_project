"""
LOT / 공정이력 DB Helper
------------------------
* 기존 insert_vision1 / update_vision2 / update_voltage 그대로 유지
* ★ upsert_process_log(lot, ...) 함수 추가  → LotNo 기반 부분 UPDATE
"""

from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Mapping, Literal
from dotenv import load_dotenv
from mysql.connector import pooling, MySQLConnection
from mysql.connector.cursor import MySQLCursor

# ─────────────────── 1) 환경 변수
load_dotenv("config.env")
DB_CONFIG: Mapping[str, str | int] = {
    "host":     os.getenv("DB_HOST","mysql"),
    "port":     int(os.getenv("DB_PORT",3306)),
    "user":     os.getenv("DB_USER","root2"),
    "password": os.getenv("DB_PW","projectteam2@"),
    "database": os.getenv("DB_NAME","secondary_battery_db"),
    "charset":  "utf8mb4",
    "autocommit":False,
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
        cur.close(); 
        conn.close()
        
# 3. LOT 번호 발급
# ──────────────────────────────────────────────────────────────────────────
PREFIX_MAP: dict[str, str] = {
    "2x3": "6P",
    "2x4": "8P",
}


def _next_lot(cur: MySQLCursor, module_type: str) -> str:
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

# ─────────────────── 6 ★ LotNo 기반 UPSERT ───────────────────
def upsert_process_log(
    lot:str,
    module_type:str,
    angle:float|None=None,
    v1:str|None=None,
    v2:str|None=None,
    volt:float|None=None,
    volt_res:str|None=None,
) -> None:
    """존재하면 UPDATE, 없으면 INSERT 후 UPDATE"""
    with get_conn_cursor() as (conn,cur):
        cur.execute(
            "INSERT IGNORE INTO module_process_log(lot_no,module_type) VALUES(%s,%s)",
            (lot,module_type)
        )
        sets, vals = [], []
        if angle is not None: sets.append("angle=%s");          vals.append(angle)
        if v1:   sets.append("vision1_result=%s");   vals.append(v1)
        if v2:   sets.append("vision2_result=%s");   vals.append(v2)
        if volt is not None: sets.append("voltage=%s");         vals.append(volt)
        if volt_res: sets.append("voltage_result=%s");          vals.append(volt_res)
        if sets:
            sql = f"UPDATE module_process_log SET {', '.join(sets)} WHERE lot_no=%s"
            cur.execute(sql, (*vals, lot))