# opcua_server.py  (FIXED)
import asyncio, os
from asyncua import Server, ua

async def main():
    LISTEN_ENDPOINT = os.getenv("UA_LISTEN_ENDPOINT", "opc.tcp://0.0.0.0:4840/inspect/server/")
    NS_URI          = os.getenv("UA_NAMESPACE",      "http://inspect.system")

    server = Server()
    await server.init()
    server.set_endpoint(LISTEN_ENDPOINT)
    server.set_server_name("Battery Inspection OPC UA")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    idx  = await server.register_namespace(NS_URI)
    insp = await server.nodes.objects.add_object(idx, "InspectSystem")

    init_vars = {
        "TargetOutput"  : (0,    ua.VariantType.Int32),
        "StartFlag"     : (False, ua.VariantType.Boolean),
        "LotNo"         : ("",   ua.VariantType.String),
        "Angle"         : (0.0,  ua.VariantType.Float),
        "Vision1Result" : ("",   ua.VariantType.String),
        "Vision2Result" : ("",   ua.VariantType.String),
        "Voltage"       : (0.0,  ua.VariantType.Float),
        "VoltageResult" : ("",   ua.VariantType.String),
        "TriggerFlag"   : (False,ua.VariantType.Boolean),
    }

    for name, (val, vtype) in init_vars.items():
        nodeid = ua.NodeId(name, idx)
        qname  = ua.QualifiedName(name, idx)
        var = await insp.add_variable(nodeid, qname, ua.Variant(val, vtype))
        await var.set_writable()

    print(f"✅ OPC UA 서버 기동 → {LISTEN_ENDPOINT}")
    print(f"✅ namespace      = {NS_URI}")
    print(f"✅ variables      = {', '.join(init_vars.keys())}")

    async with server:
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())