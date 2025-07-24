"""
opcua_to_db.py  (rev.2025-07-24)
────────────────────────────────
OPC UA Trigger → line_run / module_process_log / process_production
"""

import asyncio, os
from asyncua import Client
from dotenv import load_dotenv
from lot_db_helper import upsert_process_log, get_conn_cursor

# ── 환경 변수
load_dotenv("config.env")
UA_EP   = os.getenv("UA_ENDPOINT",  "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI  = os.getenv("UA_NAMESPACE", "http://inspect.system")
MODULE_TYPE = os.getenv("MODULE_TYPE", "2x3")

# 한 세션(line_run) 동안 유지할 라인 ID
LINE_ID: int | None = None

NODE_KEYS = [
    "StartFlag", "TargetOutput", "TriggerFlag",
    "LotNo", "Voltage", "VoltageResult"
]

# ────────────────────────────────────────────────────────────
async def process_once(nodes: dict):
    """TriggerFlag 상승 시 한 번 호출 → 공정 P03 로그 UPSERT"""
    if LINE_ID is None:
        print("⚠️ line_id 없음 → skip"); return

    lot = await nodes["LotNo"].read_value()
    if not lot:
        print("⚠️ LotNo 비어 있음 → skip"); return

    volt = await nodes["Voltage"].read_value()
    vres = await nodes["VoltageResult"].read_value()

    upsert_process_log(
        lot         = lot,
        line_id     = LINE_ID,
        module_type = MODULE_TYPE,
        process_id  = "P03",
        measure     = volt,
        result      = vres,
    )
    print(f"DB upsert → {lot}  {volt:.3f} V  ({vres})")


# ────────────────────────────────────────────────────────────
async def run_bridge():
    global LINE_ID

    while True:
        try:
            async with Client(UA_EP) as cli:
                idx  = await cli.get_namespace_index(NS_URI)
                insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
                nodes = {k: await insp.get_child([f"{idx}:{k}"]) for k in NODE_KEYS}
                print("✅ OPC UA Bridge 연결")

                prev_start = False
                while True:
                    # ① StartFlag 감시
                    start = await nodes["StartFlag"].read_value()

                    # ─ StartFlag ↑ : 새 line_run 만들기
                    if (not prev_start) and start:
                        tgt = await nodes["TargetOutput"].read_value()
                        with get_conn_cursor() as (_, cur):
                            cur.execute(
                                """INSERT INTO line_run
                                     (work_date, target_output, start_dt, line_state)
                                   VALUES (CURDATE(), %s, NOW(), 'RUNNING')""",
                                (tgt,)
                            )
                            LINE_ID = cur.lastrowid
                            print(f"line_run created → line_id={LINE_ID}")

                    # ─ StartFlag ↓ : 세션 종료
                    if prev_start and (not start) and LINE_ID:
                        with get_conn_cursor() as (_, cur):
                            cur.execute(
                                """UPDATE line_run
                                      SET line_state='COMPLETE', end_dt=NOW()
                                    WHERE line_id=%s""",
                                (LINE_ID,)
                            )
                        print(f"line_run complete → line_id={LINE_ID}")
                        LINE_ID = None

                    prev_start = start

                    # ② 공정 완료 Trigger 처리
                    trg = await nodes["TriggerFlag"].read_value()
                    if LINE_ID and trg:
                        await process_once(nodes)
                        await nodes["TriggerFlag"].write_value(False)

                    await asyncio.sleep(0.05)

        except Exception as e:
            print("⚠️ Bridge 오류:", e)
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_bridge())