"""
opcua_to_db.py  (rev.2025-07-31)
────────────────────────────────
OPC UA Trigger → module 테이블 stage 플래그 업데이트
(공정 P03 = Voltage 단계만 처리, stage 플래그는 Writer들이 세팅)
"""
import asyncio, os
from asyncua import Client
from dotenv import load_dotenv
from lot_db_helper import get_conn_cursor        # upsert_log 불필요

load_dotenv("config.env")
UA_EP  = os.getenv("UA_ENDPOINT",  "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI = os.getenv("UA_NAMESPACE", "http://inspect.system")

LINE_ID: int | None = None          # line_run 기능 보류 – 사용 안 함

NODE_KEYS = ["StartFlag", "TriggerFlag", "LotNo",
             "Voltage", "VoltageResult"]

# ───────────────────────────────────────────────────────────
async def run_bridge():
    while True:
        try:
            async with Client(UA_EP) as cli:
                idx  = await cli.get_namespace_index(NS_URI)
                insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
                nodes = {k: await insp.get_child([f"{idx}:{k}"]) for k in NODE_KEYS}
                print("✅ OPC UA Bridge connected")

                while True:
                    # Voltage 단계 완료(TriggerFlag ↑) 를 감지해 기록만 남김
                    trig = await nodes["TriggerFlag"].read_value()
                    if trig:
                        lot   = await nodes["LotNo"].read_value()
                        volt  = await nodes["Voltage"].read_value()
                        vres  = await nodes["VoltageResult"].read_value()
                        print(f"[Bridge] {lot}  {volt:.3f} V ({vres})")
                        await nodes["TriggerFlag"].write_value(False)
                    await asyncio.sleep(0.05)
        except Exception as e:
            print("⚠️ OPC UA Bridge error:", e)
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_bridge())