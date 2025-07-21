import asyncio, os, sys, time
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua

# ---------- 0) 설정 로드 ----------
load_dotenv("config.env")        # docker compose 에서도 같은 파일 공유

PLC_IP       = os.getenv("PLC_IP",      "192.168.0.10")
PLC_PORT     = int(os.getenv("PLC_PORT", "5001"))
PLC_DEVICE   = os.getenv("PLC_DEVICE",  "D100")     # 읽을 WORD 주소(예: D100)
SCALE        = float(os.getenv("VOLT_SCALE", "0.001"))
UA_ENDPOINT  = os.getenv("UA_ENDPOINT",
                          "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI       = os.getenv("UA_NAMESPACE", "http://inspect.system")

LOW_LIMIT    = float(os.getenv("VOLT_LOW_LIMIT",  "3.70"))
HIGH_LIMIT   = float(os.getenv("VOLT_HIGH_LIMIT", "4.20"))
POLL_CYCLE   = float(os.getenv("VOLT_POLL_CYCLE", "1.0"))   # 초

# ---------- 1) PLC 객체 ----------
plc = Type3E()
plc.host      = PLC_IP
plc.port      = PLC_PORT
plc.unit_code = 0xFF            # 로컬 스테이션 (필요 시 수정)

async def read_voltage_word() -> float:
    """PLC WORD 1개 읽어서 Volt 변환"""
    word = await asyncio.to_thread(
        plc.batchread_wordunits, headdevice=PLC_DEVICE, readsize=1
    )
    return round(word[0] * SCALE, 3)

async def plc_connect() -> None:
    """비동기 쓰레드에서 PLC 연결"""
    await asyncio.to_thread(plc.connect)

# ---------- 2) OPC UA 작성 루프 ----------
async def writer_loop() -> None:
    async with Client(UA_ENDPOINT) as cli:
        # 네임스페이스 index 취득
        idx = await cli.get_namespace_index(NS_URI)
        insp_obj     = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        voltage_node = await insp_obj.get_child([f"{idx}:Voltage"])
        result_node  = await insp_obj.get_child([f"{idx}:VoltageResult"])
        flag_node    = await insp_obj.get_child([f"{idx}:TriggerFlag"])

        print(f"✅ UA 연결 완료 → {UA_ENDPOINT}")

        while True:
            try:
                volt   = await read_voltage_word()
                result = "OK" if LOW_LIMIT <= volt <= HIGH_LIMIT else "NG"

                await voltage_node.write_value(ua.Variant(volt,   ua.VariantType.Float))
                await result_node.write_value( ua.Variant(result, ua.VariantType.String))
                await flag_node.write_value(   ua.Variant(True,   ua.VariantType.Boolean))

                print(
                    f"[Voltage] {time.strftime('%H:%M:%S')}  {volt:5.3f} V → {result}"
                )

            except Exception as e:
                print("⚠️  통신 오류:", e)
                # PLC 재접속 로직
                try:
                    await asyncio.to_thread(plc.close)
                except Exception:
                    pass

                await asyncio.sleep(1)
                try:
                    await plc_connect()
                    print("🔄 PLC 재연결 성공")
                except Exception:
                    print("❌ PLC 재연결 실패 · 5초 후 재시도")
                    await asyncio.sleep(5)

            await asyncio.sleep(POLL_CYCLE)
            
# ---------- 3) 엔트리 포인트 ----------
async def main() -> None:
    await plc_connect()
    print(f"✅ PLC 연결 성공  ({PLC_IP}:{PLC_PORT})")
    await writer_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n종료합니다.")
        sys.exit(0)