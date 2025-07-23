"""
OPC UA → MySQL Bridge
---------------------
TriggerFlag ↑ 시  LotNo · Angle · Vision1/2 · Voltage 값 읽어
  → upsert_process_log 로 DB 부분 UPDATE
"""

import asyncio, os
from asyncua import Client
from dotenv import load_dotenv
from lot_db_helper import upsert_process_log

load_dotenv("config.env")
UA_ENDPOINT  = os.getenv("UA_ENDPOINT","opc.tcp://opcua-server:4840/inspect/server/")
UA_NAMESPACE = os.getenv("UA_NAMESPACE","http://inspect.system")
MODULE_TYPE  = os.getenv("MODULE_TYPE","2x3")

NODE_KEYS = ["TriggerFlag","LotNo","Angle","Vision1Result",
             "Vision2Result","Voltage","VoltageResult"]

async def process_once(nodes):
    lot = await nodes["LotNo"].read_value()
    if not lot:                               # LotNo 없으면 무시
        print("⚠️ LotNo 비어 있음 → skip"); return
    angle = await nodes["Angle"].read_value()
    v1    = await nodes["Vision1Result"].read_value()
    v2    = await nodes["Vision2Result"].read_value()
    volt  = await nodes["Voltage"].read_value()
    vres  = await nodes["VoltageResult"].read_value()

    upsert_process_log(
        lot          = lot,
        module_type  = MODULE_TYPE,
        angle        = angle if angle else None,
        v1           = v1 or None,
        v2           = v2 or None,
        volt         = volt if volt else None,
        volt_res     = vres or None,
    )
    print(f"✔ DB upsert → {lot}")

async def run_bridge():
    while True:
        try:
            async with Client(UA_ENDPOINT) as cli:
                idx = await cli.get_namespace_index(UA_NAMESPACE)
                nodes={k:cli.get_node(f"ns={idx};s={k}") for k in NODE_KEYS}
                print("✅ OPC UA Bridge 연결")
                prev=False
                while True:
                    trg = await nodes["TriggerFlag"].read_value()
                    if not prev and trg:
                        await process_once(nodes)
                        await nodes["TriggerFlag"].write_value(False)
                    prev=trg; await asyncio.sleep(0.05)
        except Exception as e:
            print("⚠️ Bridge 오류:", e); await asyncio.sleep(2)

if __name__=="__main__":
    asyncio.run(run_bridge())