# opcua_server.py
import asyncio
import os
from asyncua import Server, ua

async def main():
    try:
        LISTEN_ENDPOINT = os.getenv("UA_LISTEN_ENDPOINT","opc.tcp://0.0.0.0:4840/inspect/server/")
        CLIENT_ENDPOINT = os.getenv("UA_ENDPOINT","opc.tcp://opcua-server:4840/inspect/server/")

        NS_URI = os.getenv("UA_NAMESPACE", "http://inspect.system")

        server = Server()
        await server.init()
        server.set_endpoint(LISTEN_ENDPOINT)       # 모든 인터페이스에 리슨
        server.set_server_name("Battery Inspection OPC UA")
        server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

        idx = await server.register_namespace(NS_URI)
        inspect = await server.nodes.objects.add_object(idx, "InspectSystem")

        print("▶ 변수 등록 시작")

        init_vars = {
            "Angle": (0.0, ua.VariantType.Float),
            "Vision1Result": ("", ua.VariantType.String),
            "Vision2Result": ("", ua.VariantType.String),
            "Voltage": (0.0, ua.VariantType.Float),
            "VoltageResult": ("", ua.VariantType.String),
            "TriggerFlag": (False, ua.VariantType.Boolean),
        }

        for name, (val, vtype) in init_vars.items():
            print(f"  - 변수 생성 중: {name}")
            nodeid = ua.NodeId(name, idx)
            name   = ua.QualifiedName(name, idx)
            var = await inspect.add_variable(
                nodeid,
                name,
                ua.Variant(val, vtype)
            )
            await var.set_writable()

        print(f"✅ OPC UA 서버 기동 -> {LISTEN_ENDPOINT}",flush=True)
        print(f"✅ namespace uri  = {NS_URI}",flush=True)
        print(f"✅ variables      = {', '.join(init_vars.keys())}",flush=True)

        async with server:
            while True:
                await asyncio.sleep(1)

    except Exception as e:
        print("❌ main() 루틴에서 예외 발생:", e)


if __name__ == "__main__":
    print("📌 [START] opcua_server.py 진입",flush=True)
    asyncio.run(main())
