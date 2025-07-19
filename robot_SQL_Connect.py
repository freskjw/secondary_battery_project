import os, time, threading, queue, signal, sys
from datetime import datetime
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import mysql.connector as mc
from indydcp2 import IndyDCP2
import pymcprotocol

# ───────────── 0. 환경변수 읽기 ───────────────────────────────
load_dotenv()

ROBOT_COUNT = int(os.getenv("ROBOT_COUNT", 1))
BATCH_SIZE  = int(os.getenv("BATCH_SIZE", 50))
PERIOD_MS    = int(os.getenv("COLLECT_PERIOD_MS", 1000))
# ───────────── 1. DB 커넥션 풀 ───────────────────────────────
db = mc.connect(
    host=os.getenv("MYSQL_HOST"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PW"),
    database=os.getenv("MYSQL_DB"),
    autocommit=False,
    pool_name="collector_pool",
    pool_size=8
)
cursor = db.cursor()

INSERT_SQL = """
INSERT INTO raw_robot_plc (
  source,                 -- 'robot1' ~ 'robot3' or 'plc'
  ts,
  j1, j2, j3, j4, j5, j6,         -- 로봇 토크
  elec_power, peak_power,         -- 로봇 실시간/피크 전력
  xyz_x, xyz_y, xyz_z,            -- TCP 좌표
  cycle_time_ms, robot_state,     -- 로봇
  plc_word0, plc_word1, plc_word2 -- PLC 데이터 일부(예시)
) VALUES (
  %(source)s, %(ts)s,
  %(j1)s, %(j2)s, %(j3)s, %(j4)s, %(j5)s, %(j6)s,
  %(power)s, %(peak)s,
  %(x)s, %(y)s, %(z)s,
  %(cycle)s, %(state)s,
  %(w0)s, %(w1)s, %(w2)s
)"""

# ───────────── 2. Queue & Writer 스레드 ───────────────────────
q = queue.Queue(maxsize=20000)

def db_writer():
    """Queue → pandas → executemany Batch"""
    buffer = []
    while True:
        item = q.get()
        if item is None:
            break
        buffer.append(item)
        if len(buffer) >= BATCH_SIZE:
            df = pd.DataFrame(buffer)
            # 예시: 실시간 백터 평균 계산 (NumPy) — 필요 없으면 제거
            jt_cols = [f'j{i}' for i in range(1, 7)]
            if not df[jt_cols].isna().all().all():
                mean_torque = df[jt_cols].mean().to_numpy(dtype=float)
                print("Batch 평균 토크(N·m):", np.round(mean_torque, 2))
            try:
                cursor.executemany(INSERT_SQL, df.fillna(None).to_dict("records"))
                db.commit()
                buffer.clear()
            except Exception as e:
                db.rollback()
                print("DB writer error:", e)

writer_th = threading.Thread(target=db_writer, daemon=True)
writer_th.start()

# ───────────── 3. 로봇 수집 스레드 ────────────────────────────
def robot_worker(idx: int, ip: str, port: int):
    label = f"robot{idx}"
    indy = IndyDCP2(host=ip, port=port)
    indy.connect()
    print(f"[{label}] connected")
    while True:
        try:
            jt   = indy.read_joint_torque()            # list[6]
            pose = indy.read_tcp_pose()                # [x,y,z,rx,ry,rz]
            pwr  = indy.read_power()                   # dict
            cyc  = indy.read_cycle_time()
            st   = indy.read_robot_status()

            q.put({
                "source": label,
                "ts": datetime.utcnow(),
                "j1": jt[0], "j2": jt[1], "j3": jt[2],
                "j4": jt[3], "j5": jt[4], "j6": jt[5],
                "power": pwr["inst"], "peak": pwr["peak"],
                "x": pose[0], "y": pose[1], "z": pose[2],
                "cycle": cyc, "state": st,
                # PLC 컬럼 자리 채우기
                "w0": None, "w1": None, "w2": None
            })
            time.sleep(PERIOD_MS)
        except Exception as e:
            print(f"[{label}] error:", e)
            time.sleep(2)

# ───────────── 4. PLC 수집 스레드 ─────────────────────────────
def plc_worker():
    label = "plc"
    mc = pymcprotocol.Type3E()
    mc.setaccessopt(
        iProtocol = pymcprotocol.Constants.PROTOCOL_DTCP,
        iNetworkNo=0, iStationNo=0, iServerIPAddress=os.getenv("PLC_IP"),
        iServerPort=int(os.getenv("PLC_PORT", 5000))
    )
    start_d = os.getenv("PLC_START_DEVICE", "D100")
    words   = int(os.getenv("PLC_WORDS", 31))
    while True:
        try:
            data = mc.batchread_random(word_devices=[f"{start_d}{i}" for i in range(words)])
            # 예시: 첫 세 word 만 저장
            q.put({
                "source": label, "ts": datetime.utcnow(),
                # 로봇 컬럼 자리 채우기
                "j1": None, "j2": None, "j3": None, "j4": None, "j5": None, "j6": None,
                "power": None, "peak": None, "x": None, "y": None, "z": None,
                "cycle": None, "state": None,
                "w0": data[0], "w1": data[1], "w2": data[2]
            })
            time.sleep(PERIOD_MS)
        except Exception as e:
            print("[PLC] error:", e)
            time.sleep(2)

# ───────────── 5. 스레드 기동 ────────────────────────────────
workers = []

for i in range(1, ROBOT_COUNT + 1):
    ip   = os.getenv(f"ROBOT{i}_IP")
    port = int(os.getenv(f"ROBOT{i}_PORT", 7575))
    t = threading.Thread(target=robot_worker, args=(i, ip, port), daemon=True)
    t.start()
    workers.append(t)

plc_th = threading.Thread(target=plc_worker, daemon=True)
plc_th.start()
workers.append(plc_th)

# ───────────── 6. 종료 처리 ─────────────────────────────────
def graceful_exit(signum, frame):
    print("Stopping…")
    q.put(None)          # writer 종료 신호
    writer_th.join(timeout=5)
    cursor.close(); db.close()
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

while True:
    time.sleep(5)        # 메인 스레드는 대기만