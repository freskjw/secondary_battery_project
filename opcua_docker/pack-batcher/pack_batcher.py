# v6 ★ PATCHED: 양품만, 2개→1팩, LOT포맷 KCP-6P/8P-001
import time
from datetime import datetime
from lot_db_helper import get_conn_cursor, _db_to_label

SCAN_SEC = 1.5

def make_pack_if_ready(db_type: str):
    """db_type: '2x3' or '2x4'"""
    label = _db_to_label(db_type)  # '6P' / '8P'
    with get_conn_cursor() as (cnx, cur):
        # 양품만 + 미매핑
        cur.execute("""
            SELECT m.lot_no, m.voltage
              FROM module m
             WHERE m.module_type=%s
               AND m.is_scrap=0
               AND m.v1_ok=1
               AND m.v2_ok=1
               AND m.voltage_ok=1
               AND m.lot_no NOT IN (SELECT module_lot_no FROM pack_module_map)
             ORDER BY m.created_at DESC
             LIMIT 2
        """, (db_type,))
        rows = cur.fetchall()
        if len(rows) < 2:
            return False

        voltages = [r[1] for r in rows if r[1] is not None]
        vavg = round(sum(voltages)/len(voltages), 3) if voltages else None

        # LOT 생성: KCP-6P/8P-001
        cur.execute("UPDATE pack_tracker SET last_serial=last_serial+1 WHERE pack_type=%s", (label,))
        cur.execute("SELECT last_serial FROM pack_tracker WHERE pack_type=%s", (label,))
        serial = cur.fetchone()[0]
        pack_lot = f"KCP-{label}-{serial:03d}"

        cur.execute("""
            INSERT INTO pack (pack_lot_no, pack_type, pack_voltage, completed_at)
            VALUES (%s,%s,%s,NOW(3))
        """, (pack_lot, db_type, vavg))

        for (lot_no, _) in rows:
            cur.execute("""
              INSERT INTO pack_module_map (pack_lot_no, module_lot_no)
              VALUES (%s,%s)
            """, (pack_lot, lot_no))
            cur.execute("""
              UPDATE module_process_log
                 SET pack_lot_no=%s
               WHERE lot_no=%s
            """, (pack_lot, lot_no))

        print(f"[PACK] {pack_lot} ({db_type})  2 modules  Vavg={vavg}  @ {datetime.now():%H:%M:%S.%f}")
        return True

def run_forever():
    while True:
        made = False
        for t in ("2x3", "2x4"):
            made |= bool(make_pack_if_ready(t))
        time.sleep(0.2 if made else SCAN_SEC)

if __name__ == "__main__":
    run_forever()