# vision1_writer.py
# 비전 값 쓰기
import asyncio, os, random, time
from asyncua import Client, ua

UA_ENDPOINT = os.getenv("UA_ENDPOINT", "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI      = os.getenv("UA_NAMESPACE", "http://inspect.system")
INTERVAL    = float(os.getenv("V1_INTERVAL", 2.0))
USE_SIM = os.getenv("USE_SIMULATION", "true").lower() == "true"

async def main():
    cli = Client(UA_ENDPOINT)

    # 1) 서버가 준비될 때까지 최대 30초 재시도
    for i in range(30):
        try:
            await cli.connect()
            print(f"✔ OPC UA 서버에 연결됨 → {UA_ENDPOINT}")
            break
        except OSError:
            print(f"❗ 연결 실패, 1초 뒤 재시도… ({i+1}/30)")
            await asyncio.sleep(1)
    else:
        print("❌ 서버 연결 실패, 종료합니다.")
        return

    # 2) 네임스페이스 인덱스 가져오기
    idx = await cli.get_namespace_index(NS_URI)
    print(f"▶ 네임스페이스 {NS_URI} 의 인덱스 = {idx}")

    # 3) NodeId 문자열로 바로 변수 노드 얻기
    angle_node  = cli.get_node(f"ns={idx};s=Angle")
    result_node = cli.get_node(f"ns={idx};s=Vision1Result")
    flag_node   = cli.get_node(f"ns={idx};s=TriggerFlag")

    print(f"✔ Vision1 writer 준비 완료 (주기 {INTERVAL}s)")
    
    try:
        while True:
            if USE_SIM:
                angle  = round(random.uniform(-5, 5), 2)
                result = random.choice(["OK", "NG"])
            else:
                # 실제 머신 비전 처리 후 데이터 받는 코드 (자체 Vision API 혹은 OpenCV 코드로 교체)
                #frame = capture_frame()
                #angle, result = vision_inspect(frame)
                angle, result = get_real_vision1()  # 예시 함수

            await angle_node.write_value( ua.Variant(angle,  ua.VariantType.Float) )
            await result_node.write_value( ua.Variant(result, ua.VariantType.String) )
            await flag_node.write_value(   ua.Variant(True,   ua.VariantType.Boolean) )

            print(f"[Vision-1] {time.strftime('%H:%M:%S')}  angle={angle:+5.2f}°, result={result}")
            await asyncio.sleep(INTERVAL)
    finally:
        await cli.disconnect()

if __name__ == "__main__":
    asyncio.run(main())