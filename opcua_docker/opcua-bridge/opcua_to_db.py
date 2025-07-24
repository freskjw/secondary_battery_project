"""
opcua_to_db.py  (rev.2025-07-24)
────────────────────────────────
OPC UA Trigger → module_process_log UPSERT
"""

import asyncio, os
from asyncua import Client
from dotenv import load_dotenv
from lot_db_helper import upsert_process_log

load_dotenv("config.env")
UA_EP   = os.getenv("UA_ENDPOINT","opc.tcp://opcua-server:4840/inspect/server/")
NS_URI  = os.getenv("UA_NAMESPACE","http://inspect.system")
LINE_ID = int(os.getenv("LINE_ID", "1"))
MODULE_TYPE = os.getenv("MODULE_TYPE","2x3")

NODE_KEYS = ["TriggerFlag","LotNo","Voltage","VoltageResult"]

async def process_once(nodes):
    lot  = await nodes["LotNo"].read_value()
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
    print(f"DB upsert → {lot}  {volt:.3f} V ({vres})")

async def run_bridge():
    while True:
        try:
            async with Client(UA_EP) as cli:
                idx = await cli.get_namespace_index(NS_URI)
                insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
                nodes = {k: await insp.get_child([f"{idx}:{k}"]) for k in NODE_KEYS}
                print("✅ OPC UA Bridge 연결")
                prev = False
                while True:
                    trg = await nodes["TriggerFlag"].read_value()
                    if not prev and trg:
                        await process_once(nodes)
                        await nodes["TriggerFlag"].write_value(False)
                    prev = trg
                    await asyncio.sleep(0.05)
        except Exception as e:
            print("⚠️ Bridge 오류:", e)
            await asyncio.sleep(2)

if __name__=="__main__":
    asyncio.run(run_bridge())