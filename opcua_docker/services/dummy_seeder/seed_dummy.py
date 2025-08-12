from __future__ import annotations
import os, random, math, statistics
import datetime as dt
from zoneinfo import ZoneInfo
import time, mysql.connector
from dotenv import load_dotenv

load_dotenv("/app/config.env")

def pick(*vals):
    for v in vals:
        if v is not None and str(v).strip() != "":
            return v
    return None

KST = ZoneInfo("Asia/Seoul")

def env(name, default=None): return os.getenv(name, default)

DB = dict(
    host=pick(os.getenv("REPORT_DB_HOST"), os.getenv("DB_HOST"), "mysql"),
    port=int(pick(os.getenv("REPORT_DB_PORT"), os.getenv("DB_PORT"), "3306")),
    user=pick(os.getenv("REPORT_DB_USER"), os.getenv("DB_USER"), "root"),
    password=pick(os.getenv("REPORT_DB_PW"), os.getenv("DB_PW"), "projectteam2@@"),
    database=pick(os.getenv("REPORT_DB_NAME"), "secondary_battery_dummy_db"),
)

# ===== 기본 크기/분포(가볍고 리포트 충분히 채워짐) =====
DAYS=int(env("DUMMY_DAYS", 28))         # 최근 28일
PER=int(env("DUMMY_PER_DAY", 8))        # 하루 8개(6P/8P 합계 → 타입별 4개)
MEAN=float(env("DUMMY_VOLT_MEAN", 8.0))
STD=float(env("DUMMY_VOLT_STD", 0.10))
VNG=float(env("DUMMY_VOLT_NG_RATE", 0.06))
VVIS=float(env("DUMMY_VISION_NG_RATE", 0.03))
LSL=float(env("VOLTAGE_LSL", 7.7))
USL=float(env("VOLTAGE_USL", 8.3))
PACK_SIZE=int(env("PACK_SIZE", 3))

def conn():
    for i in range(60):  # 최대 60회, 약 2분
        try:
            return mysql.connector.connect(**DB, autocommit=True)
        except mysql.connector.Error as e:
            print(f"[seed] waiting mysql... ({i+1}/60) {e}")
            time.sleep(2)
    raise RuntimeError("MySQL not reachable after retries")

def one(cur, sql, params=None):
    cur.execute(sql, params or ()); r=cur.fetchone()
    return (list(r.values())[0] if isinstance(r, dict) else r[0]) if r else None

def ensure_defect_seed(cur):
    cur.execute("""
    INSERT INTO defect_code(code, category, source, severity, description) VALUES
      ('VLOW','VOLT','PLC','MAJOR','Voltage below LSL'),
      ('VHIGH','VOLT','PLC','MAJOR','Voltage above USL'),
      ('VNG','VOLT','PLC','MAJOR','Voltage out of spec (generic)'),
      ('VIS_MISS','VISION','V1','CRITICAL','Missing cell detected'),
      ('VIS_ANGLE','VISION','V1','MAJOR','Angle out of tolerance'),
      ('VIS_ORIENT','VISION','V2','MAJOR','Orientation/assembly error'),
      ('OTHER_STATION','OTHER','SYS','MINOR','Other station issue')
    ON DUPLICATE KEY UPDATE enabled=VALUES(enabled)
    """)

def next_lot(cur, prefix):
    cur.execute("SELECT next_lot(%s)", (prefix,))
    r = cur.fetchone()
    return list(r.values())[0] if isinstance(r, dict) else r[0]

def insert_module(cur, lot_no, mtype, v, v1r, v2r, created):
    vres = "OK" if LSL <= v <= USL else "NG"
    cur.execute("""
      INSERT INTO module(lot_no,module_type,angle,angle_result,vision1_result,vision2_result,voltage,voltage_result,stage,created_at,updated_at)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'DONE',%s,%s)
      ON DUPLICATE KEY UPDATE voltage=VALUES(voltage), voltage_result=VALUES(voltage_result),
                              vision1_result=VALUES(vision1_result), vision2_result=VALUES(vision2_result),
                              updated_at=VALUES(updated_at)
    """, (lot_no, mtype, 0.0, "OK", v1r, v2r, v, vres, created, created))
    return vres

def insert_defect_if_ng(cur, lot_no, v, vres, v1r, v2r, created):
    if vres == "NG":
        code = "VLOW" if v < LSL else ("VHIGH" if v > USL else "VNG")
        cur.execute("""
          INSERT INTO module_defect(lot_no, defect_code, station, score, meta, detected_at)
          VALUES (%s,%s,'VOLT',NULL,NULL,%s)
        """, (lot_no, code, created))
    if v1r == "NG":
        cur.execute("INSERT INTO module_defect(lot_no, defect_code, station, detected_at) VALUES (%s,'VIS_ANGLE','VISION1',%s)", (lot_no, created))
    if v2r == "NG":
        cur.execute("INSERT INTO module_defect(lot_no, defect_code, station, detected_at) VALUES (%s,'VIS_ORIENT','VISION2',%s)", (lot_no, created))

def seed_day(cur, day):
    # 균등하게 6P/8P 반반
    per_type = PER // 2
    rows = []
    for mtype in ("6P","8P"):
        for _ in range(per_type):
            v = random.gauss(MEAN, STD)
            # NG 꼬리 분포 조금 추가
            if random.random() < max(0, VNG - 0.01):
                v = LSL - abs(random.gauss(0.2, 0.05)) if random.random()<0.5 else USL + abs(random.gauss(0.2,0.05))
            v1r = "NG" if random.random() < VVIS else "OK"
            v2r = "NG" if random.random() < VVIS else "OK"
            lot_no = next_lot(cur, f"KCM-{mtype}")
            created = dt.datetime.combine(day, dt.time(hour=random.randint(0,23), minute=random.randint(0,59), tzinfo=KST))
            vres = insert_module(cur, lot_no, mtype, round(v, 3), v1r, v2r, created)
            insert_defect_if_ng(cur, lot_no, v, vres, v1r, v2r, created)
            rows.append((mtype, lot_no, float(v), vres, created))
    return rows

def make_packs_for_day(cur, mtype, day):
    cur.execute("""
      SELECT m.lot_no, m.created_at
      FROM module m
      LEFT JOIN pack_module pm ON pm.lot_no=m.lot_no
      WHERE m.stage='DONE' AND pm.lot_no IS NULL
        AND m.module_type=%s
        AND DATE(m.created_at)=DATE(%s)
      ORDER BY m.created_at ASC
    """, (mtype, day))
    lot_rows = cur.fetchall()
    lot_list = [(r[0], r[1]) for r in lot_rows]

    for i in range(0, len(lot_list)//PACK_SIZE * PACK_SIZE, PACK_SIZE):
        pack_time = max(lot_list[i+j][1] for j in range(PACK_SIZE)) or dt.datetime.combine(day, dt.time(15,0, tzinfo=KST))
        pack_no = next_lot(cur, f"KCP-{mtype}")
        cur.execute("INSERT INTO pack(pack_no, module_type, created_at) VALUES(%s,%s,%s)", (pack_no, mtype, pack_time))
        for j in range(PACK_SIZE):
            cur.execute("INSERT INTO pack_module(pack_no, lot_no) VALUES(%s,%s)", (pack_no, lot_list[i+j][0]))

def compute_cp(cur, mtype):
    cur.execute("SELECT voltage FROM module WHERE module_type=%s AND voltage IS NOT NULL ORDER BY created_at DESC LIMIT 200", (mtype,))
    vals = [float(r[0]) for r in cur.fetchall()]
    if len(vals) < 20: return
    mean = statistics.fmean(vals); std = statistics.pstdev(vals)
    if std == 0: return
    cp  = (USL - LSL) / (6*std)
    cpk = min((USL-mean)/(3*std), (mean-LSL)/(3*std))
    cur.execute("""
      INSERT INTO process_capability(module_type, window_size, mean_v, std_v, cp, cpk, lsl, usl)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (mtype, len(vals), mean, std, cp, cpk, LSL, USL))

def main():
    with conn() as c:
        cur = c.cursor()
        ensure_defect_seed(cur)
        today = dt.datetime.now(KST).date()
        # 과거 → 오늘 직전까지 생성
        for d in range(DAYS, 0, -1):
            day = today - dt.timedelta(days=d)
            seed_day(cur, day)
            for t in ("6P","8P"):
                make_packs_for_day(cur, t, day)
        # 마지막에 CP 계산(최근치 기준)
        for t in ("6P","8P"):
            compute_cp(cur, t)
        print("[dummy-seeder] done.")

if __name__ == "__main__":
    main()
