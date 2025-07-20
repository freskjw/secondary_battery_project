from asyncua import Client
import asyncio

async def push_vision_result(angle_val, result_val, module_var):
    clinet = Client("opc.tcp://localhost:4840/vision/server/")
    await client.connect()
    
    try:
        angle = client.get_node("ns=2; s=VisionSystem/Angle")
        result = client.get_node("ns=2; s=VisionSystem/Result")
        module = client.get_node("ns=2; s=VisionSystem/ModuleType")
        trigger = client.get_node("ns=2; s=VisionSystem/TriggerFlag")
        
        await angle.write_value(angle_val)
        await result.write_value(result_val)
        await module.write_value(module_var)
        await trigger.write_value(True)
        print(" 비전 결과 OPC UA에 전송완료")
        
    finally:
        await client.disconnect()
        print("클라이언트 연결 종료")