from asyncua import Server
import asyncio

async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/vision/server/")
    idx = await server.register_namespace("http://vision.local")
    
    vision = await server.nodes.objects.add_object(idx, "VisionSystem")
    angle = await vision.add_variable(idx, "Angle", 0.0)
    result = await vision.add_variable(idx, "Result", 0.0)
    module_type = await vision.add_variable(idx, "ModuleType", "")
    trigger = await vision.add_variable(idx, "TriggerFlag", False)
    
    for var in [angle, result, module_type, trigger]:
        await var.set_writable()
        
    print("OPU UA 서버 실행 중...")
    async with server:
        while True:
            await asyncio.sleep(1)
            
if __name__ == "__main__":
    asyncio.run(main())