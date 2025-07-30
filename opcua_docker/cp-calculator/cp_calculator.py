# cp_calculator.py  (rev.2025-07-24)

import time, os, mysql.connector, numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("config.env")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT",3306)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PW"),
    "database": os.getenv("DB_NAME"),
}
LSL = float(os.getenv("VOLT_LOW_LIMIT",3.70))
USL = float(os.getenv("VOLT_HIGH_LIMIT",4.20))
INTERVAL = float(os.getenv("CP_POLL_CYCLE",10.0))

def compute_cp_cpk(arr:np.ndarray):
    # numpy 가 Decimal 배열을 받으면 Decimal 반환 → 한 번 더 float() 캐스팅
    mu, sigma = float(arr.mean()), float(arr.std(ddof=1))
    if sigma<=0: return 0.0,0.0
    cp  = (USL-LSL)/(6*sigma)
    cpk = min((USL-mu)/(3*sigma),(mu-LSL)/(3*sigma))
    return cp,cpk

def run():
    conn = mysql.connector.connect(**DB_CONFIG, autocommit=True)
    cur  = conn.cursor()
    print("▶ CP-Calculator 시작")

    QUERY = """
    SELECT product_type, voltage
    FROM module
    WHERE voltage_ok = 1
    """

    while True:
        cur.execute(QUERY); rows = cur.fetchall()
        print(f"[{datetime.now():%H:%M:%S}] OK 레코드 수 = {len(rows)}")
        if rows:
            bucket={}
            for mtype,val in rows: bucket.setdefault(mtype,[]).append(val)
            for mtype, vals in bucket.items():
                vals = [float(v) for v in vals]            # ← 추가
                cp, cpk = compute_cp_cpk(np.array(vals))

                table = f"process_capability_{mtype}"   # process_capability_2x3 / 2x4
                cur.execute(f"""
                            INSERT INTO {table}
                            (calc_time, module_type, cp_voltage, cpk_voltage)
                            VALUES (%s,%s,%s,%s)""", (datetime.now(), mtype, cp, cpk)
                            )
                print(f"  {mtype} → Cp={cp:.3f}, Cpk={cpk:.3f}")
        time.sleep(INTERVAL)

if __name__=="__main__":
    run()