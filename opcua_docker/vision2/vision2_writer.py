import asyncio, os, random, time
from asyncua import Client, ua

# ---------- 1) 환경 설정 ----------
UA_ENDPOINT = os.getenv(
    "UA_ENDPOINT",
    "opc.tcp://opcua-server:4840/inspect/server/"   # compose 네트워크에서 서비스명 사용
)
NS_URI      = os.getenv("UA_NAMESPACE", "http://inspect.system")
INTERVAL    = float(os.getenv("V2_INTERVAL", 2.0))
USE_SIM     = os.getenv("USE_SIMULATION", "true").lower() == "true"

async def main() -> None:
    # 1) 서버 연결 재시도 루프
    while True:
        try:
            async with Client(UA_ENDPOINT) as cli:
                # namespace index 확보
                idx = await cli.get_namespace_index(NS_URI)

                # InspectSystem 객체 및 노드 바인딩
                insp_obj    = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
                result_node = await insp_obj.get_child([f"{idx}:Vision2Result"])
                flag_node   = await insp_obj.get_child([f"{idx}:TriggerFlag"])

                print(f"✅ Vision-2 writer 연결 완료 → {UA_ENDPOINT}")

                # 2) 정상 연결되면 쓰기 루프 진입
                while True:
                    if USE_SIM:
                        result = random.choice(["OK", "NG"])
                    else:
                        # 실제 머신 비전 처리 후 데이터 받는 코드 (자체 Vision API 혹은 OpenCV 코드로 교체)
                        #frame = capture_frame()
                        #angle, result = vision_inspect(frame)
                        result = get_real_vision2()  # 예시 함수

                    await result_node.write_value(ua.Variant(result, ua.VariantType.String))
                    await flag_node.write_value(ua.Variant(True,   ua.VariantType.Boolean))

                    print(f"[Vision-2] {time.strftime('%H:%M:%S')}  result={result}")
                    await asyncio.sleep(INTERVAL)
        except (OSError, asyncio.TimeoutError) as e:
            # 연결 실패 시 재시도
            print("⚠️ Vision-2 UA 연결 실패:", e, "→ 5초 후 재시도")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())