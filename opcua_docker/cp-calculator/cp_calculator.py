# cp_calculator.py  (rev.2025-07-30 ― DB 스키마에 맞춤)

import time, os, mysql.connector, numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("config.env")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PW"),
    "database": os.getenv("DB_NAME"),
}
LSL = float(os.getenv("VOLT_LOW_LIMIT", 3.70))
USL = float(os.getenv("VOLT_HIGH_LIMIT", 4.20))
INTERVAL = float(os.getenv("CP_POLL_CYCLE", 10.0))


def compute_cp_cpk(arr: np.ndarray):
    mu, sigma = float(arr.mean()), float(arr.std(ddof=1))
    if sigma <= 0:
        return 0.0, 0.0
    cp  = (USL - LSL) / (6 * sigma)
    cpk = min((USL - mu) / (3 * sigma), (mu - LSL) / (3 * sigma))
    return cp, cpk


def run() -> None:
    conn = mysql.connector.connect(**DB_CONFIG, autocommit=True)
    cur  = conn.cursor(dictionary=False)
    print("▶ CP-Calculator 시작")

    # --- 여기만 수정 --------------------------------------------------
    QUERY = """
        SELECT module_type,
               measure_value               -- voltage → measure_value
        FROM   module_process_log
        WHERE  process_id = 'P03'
          AND  result     = 'OK'
    """
    # ----------------------------------------------------------------

    while True:
        cur.execute(QUERY)
        rows = cur.fetchall()
        print(f"[{datetime.now():%H:%M:%S}] OK 레코드 수 = {len(rows)}")

        if rows:
            buckets = {}
            for mtype, val in rows:
                buckets.setdefault(mtype, []).append(float(val))

            for mtype, vals in buckets.items():
                cp, cpk = compute_cp_cpk(np.array(vals))

                table = f"process_capability_{mtype}"   #  process_capability_2x3 / 2x4
                cur.execute(
                    f"""INSERT INTO {table}
                        (calc_time, module_type, cp_voltage, cpk_voltage)
                        VALUES (%s, %s, %s, %s)
                    """,
                    (datetime.now(), mtype, cp, cpk)
                )
                print(f"  {mtype} → Cp={cp:.3f}, Cpk={cpk:.3f}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()