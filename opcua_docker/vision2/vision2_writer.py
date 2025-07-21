import asyncio, os, random, time
from asyncua import Client, ua

# ---------- 1) 환경 설정 ----------
UA_ENDPOINT = os.getenv(
    "UA_ENDPOINT",
    "opc.tcp://opcua-server:4840/inspect/server/"   # compose 네트워크에서 서비스명 사용
)
NS_URI      = os.getenv("UA_NAMESPACE", "http://inspect.system")
INTERVAL    = float(os.getenv("V2_INTERVAL", 2.0))

async def main() -> None:
    async with Client(UA_ENDPOINT) as cli:
        # 네임스페이스 인덱스 확보
        idx = await cli.get_namespace_index(NS_URI)

        insp_obj    = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        result_node = await insp_obj.get_child([f"{idx}:Vision2Result"])
        flag_node   = await insp_obj.get_child([f"{idx}:TriggerFlag"])

        print(f"✅ Vision-2 writer 연결 완료 → {UA_ENDPOINT}")
        while True:
            # ---- 가상 Vision-2 결과 생성 ----
            result = random.choice(["OK", "NG"])

            # ---- 값 쓰기 (데이터타입 맞춤) ----
            await result_node.write_value(ua.Variant(result, ua.VariantType.String))
            await flag_node.write_value(ua.Variant(True,   ua.VariantType.Boolean))

            print(f"[Vision-2] {time.strftime('%H:%M:%S')}  result={result}")

            await asyncio.sleep(INTERVAL)
            
if __name__ == "__main__":
    asyncio.run(main())