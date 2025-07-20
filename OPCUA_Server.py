import asyncio
from asyncua import Server,ua

async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/inspect/server/")
    server.set_server_name("Battery Inspection OPC UA")
    
    idx = await server.register_namespace("http://inspect.system")
    
    inspect = await server.nodes.objects.add_object(idx, "InspectSystem")
    
    init_vars = {
        "Angle"         : 0.0,
        "Vision1Result" : "",
        "Vision2Result" : "",
        "Voltage"       : 0.0,
        "VoltageResult" : "",
        "TriggerFlag"   : False,
    }
    for name, val in init_vars.items():
        string_nodeid = ua.NodeId(f"InspectSystem/{name}", idx)
        var = await inspect.add_variable(idx, name, val, nodeid = string_nodeid)
        await var.set_writable()
        
    print(" OPC UA 서버 시작")
    async with server:
        while True:
            await asyncio.sleep(1)
            
if __name__ == "__main__":
    asyncio.run(main())