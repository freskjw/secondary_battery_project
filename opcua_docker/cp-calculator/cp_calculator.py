# cp_calculator.py

import time
import os
import mysql.connector
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# 1) 환경 변수 로드
load_dotenv("config.env")

# 2) DB 접속 설정
DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PW"),
    "database": os.getenv("DB_NAME"),
}

# 3) 사양 한계, 인터벌
LSL = float(os.getenv("VOLT_LOW_LIMIT", 3.70))
USL = float(os.getenv("VOLT_HIGH_LIMIT", 4.20))
INTERVAL = float(os.getenv("CP_POLL_CYCLE", 10.0))

# 지원 모듈
VALID_MODULES = {"2x3", "2x4"}


def compute_cp_cpk(volts: np.ndarray):
    mu    = volts.mean()
    sigma = volts.std(ddof=1)
    if sigma <= 0:
        return 0.0, 0.0
    Cp  = (USL - LSL) / (6 * sigma)
    Cpk = min((USL - mu) / (3 * sigma), (mu - LSL) / (3 * sigma))
    return Cp, Cpk


def get_db_connection():
    """DB 연결 → autocommit 모드 설정 → 반환"""
    while True:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            conn.autocommit = True
            print("✅ DB 연결 성공 (autocommit enabled)")
            return conn
        except Exception as e:
            print("⚠️ DB 연결 실패, 5초 후 재시도:", e)
            time.sleep(5)


def run():
    conn = get_db_connection()
    cursor = conn.cursor()
    print("▶ CP-Calculator 시작")

    while True:
        # 1) OK 전압 조회
        cursor.execute("""
            SELECT module_type, voltage
              FROM module_process_log
             WHERE voltage_result = 'OK'
             ORDER BY voltage_timestamp
        """)
        rows = cursor.fetchall()
        print(f"[{datetime.now():%H:%M:%S}] OK 레코드 수 = {len(rows)}")

        if rows:
            # 2) 모듈별 묶기
            by_type: dict[str, list[float]] = {}
            for mtype, voltage in rows:
                by_type.setdefault(mtype, []).append(voltage)

            # 3) 각 모듈별 Cp/Cpk 계산 & INSERT
            for mtype, volt_list in by_type.items():
                if mtype not in VALID_MODULES:
                    print(f"⚠️ 알 수 없는 module_type '{mtype}' 스킵")
                    continue

                cp, cpk = compute_cp_cpk(np.array(volt_list))
                table_name = f"process_capability_{mtype}"
                sql = f"""
                    INSERT INTO {table_name}
                      (calc_time, module_type, cp_voltage, cpk_voltage)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (datetime.now(), mtype, cp, cpk))
                # 명시적 커밋
                conn.commit()
                print(f"[{datetime.now():%H:%M:%S}] {mtype} → Cp={cp:.3f}, Cpk={cpk:.3f}")
        else:
            print(f"[{datetime.now():%H:%M:%S}] OK 데이터 없음")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()