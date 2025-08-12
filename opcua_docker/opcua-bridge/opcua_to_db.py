"""
opcua_to_db.py (v5.1)
- 현재는 TriggerFlag를 모니터링하여 콘솔에만 기록(옵션)
"""
import asyncio, os
from asyncua import Client
from dotenv import load_dotenv

load_dotenv("config.env")
UA_EP  = os.getenv("UA_ENDPOINT",  "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI = os.getenv("UA_NAMESPACE", "http://inspect.system")

NODE_KEYS = ["StartFlag", "TriggerFlag", "LotNo", "Voltage", "VoltageResult"]

async def run_bridge():
    while True:
        try:
            async with Client(UA_EP) as cli:
                idx  = await cli.get_namespace_index(NS_URI)
                insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
                nodes = {k: await insp.get_child([f"{idx}:{k}"]) for k in NODE_KEYS}
                print("✅ OPC UA Bridge connected")

                while True:
                    if await nodes["TriggerFlag"].read_value():
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