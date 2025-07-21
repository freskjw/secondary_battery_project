# cp_calculator.py
import time, os
import mysql.connector
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("config.env")

DB = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PW"),
    "database": os.getenv("DB_NAME"),
}

LSL = float(os.getenv("VOLT_LOW_LIMIT", 3.70))
USL = float(os.getenv("VOLT_HIGH_LIMIT",4.20))
INTERVAL = float(os.getenv("CP_POLL_CYCLE", 10.0))  # 초

def compute_cp_cpk(volts: np.ndarray):
    mu    = volts.mean()
    sigma = volts.std(ddof=1)
    Cp  = (USL - LSL) / (6 * sigma) if sigma>0 else 0
    Cpk = min((USL-mu)/(3*sigma), (mu-LSL)/(3*sigma)) if sigma>0 else 0
    return Cp, Cpk

def run():
    conn = mysql.connector.connect(**DB)
    cursor = conn.cursor()
    while True:
        # 1) OK 전압 전부 조회 (module_type별 계산하려면 GROUP BY)
        cursor.execute("""
            SELECT module_type, voltage
              FROM module_process_log
             WHERE voltage_result='OK'
        """)
        rows = cursor.fetchall()
        if rows:
            # module_type별로 묶어서 계산
            by_type = {}
            for mtype, v in rows:
                by_type.setdefault(mtype, []).append(v)
            for mtype, vs in by_type.items():
                volts = np.array(vs)
                cp, cpk = compute_cp_cpk(volts)
                # 2) 결과 INSERT
                cursor.execute("""
                    INSERT INTO process_capability
                      (calc_time,module_type,cp_voltage,cpk_voltage)
                    VALUES (%s,%s,%s,%s)
                """, (datetime.now(), mtype, cp, cpk))
            conn.commit()
        time.sleep(INTERVAL)

if __name__=="__main__":
    run()