# ────────────────────────────────
# healthcheck/ua_ping.py
# ────────────────────────────────
import os
from asyncua import Client
import asyncio
import sys

UA_ENDPOINT = os.getenv("UA_ENDPOINT", "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI      = os.getenv("UA_NAMESPACE", "http://inspect.system")

async def ping():
    try:
        async with Client(UA_ENDPOINT) as client:
            idx = await client.get_namespace_index(NS_URI)
            insp = await client.nodes.objects.get_child([f"{idx}:InspectSystem"])
            test_node = await insp.get_child([f"{idx}:Angle"])
            val = await test_node.read_value()
            print(f"✅ OPC UA 서버 정상 응답: Angle = {val}")
            sys.exit(0)
    except Exception as e:
        print("❌ OPC UA 서버 연결 실패:", e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(ping())