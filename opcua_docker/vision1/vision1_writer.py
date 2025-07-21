import asyncio, os, random, time
from asyncua import Client

# 환경 설정
UA_ENDPOINT = os.getenv("UA_ENDPOINT", "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI = os.getenv("UA_NAMESPACE", "http://inspect.system")
INTERVAL = float(os.getenv("V1_INTERVAL", 2.0))

async def main():
    async with Client(UA_ENDPOINT) as cli:
        # 네임스페이스 인덱스 동적 확보
        idx = await cli.get_namespace_index(NS_URI)
        
        insp_obj            = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        angle_node   = await insp_obj.get_child([f"{idx}:Angle"])
        result_node  = await insp_obj.get_child([f"{idx}:Vision1Result"])
        flag_node    = await insp_obj.get_child([f"{idx}:TriggerFlag"])
        
        print(f" Vision-1 writer 연결 완료 -> {UA_ENDPOINT}")
        
        while True:
            # ---- 가상 계측값 생성 ----
            angle  = round(random.uniform(-5, 5), 2)          # ±5 deg
            result = random.choice(["OK", "NG"])
            
            # ---- 값 쓰기 (데이터타입 맞춤) ----
            await angle_node.write_value(ua.Variant(angle,  ua.VariantType.Float))
            await result_node.write_value(ua.Variant(result, ua.VariantType.String))
            await flag_node.write_value(ua.Variant(True,   ua.VariantType.Boolean))
            
            print(f"[Vision-1] {time.strftime('%H:%M:%S')}  "
                  f"angle={angle:5.2f}°,  result={result}")
            
            await asyncio.sleep(INTERVAL)
            
if __name__ == "__main__":
    asyncio.run(main())