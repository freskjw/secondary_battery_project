import asyncio, os, sys
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client

load_dotenv("config.env")

PLC_IP          = os.getenv("PLC_IP")               # PLC IP 주소
PLC_PORT        = int(os.getenv("PLC_PORT"))        # PLC PORT 번호
PLC_DEVICE      = os.getenv("PLC_DEVICE")           # 전압 WORD 주소
SCALE           = float(os.getenv("VOLT_SCALE"))    # Volt 스케일 조정
UA_ENDPOINT     = os.getenv("UA_ENDPOINT")          # OPC UA 주소

low_limit   = float("3.70")   # 전압 하한값(변경 가능)
high_limit  = float("4.20")   # 전압 상한값(변경 가능)

plc             = Type3E()
plc.host        = PLC_IP
plc.port        = PLC_PORT
plc.unit_code   = 0xFF          # 기본값(로컬 스테이션)  - 필요시 수정

async def read_voltage_word():
    word = await asyncio.to_thread(
        plc.batchread_wordunits, headdevice=PLC_DEVICE, readsize=1
    )
    return round(word[0] * SCALE, 3)

async def plc_connect():
    await asyncio.to_thread(plc.connect)

async def writer_loop():
    async with Client(UA_ENDPOINT) as cli:
        inspect = "ns=2;s=InspectSystem/"
        v_node  = cli.get_node(inspect + "Voltage")
        r_node  = cli.get_node(inspect + "VoltageResult")
        t_node  = cli.get_node(inspect + "TriggerFlag")
        
        while True:
            try:
                volt = await read_voltage_word()
                result = "OK" if low_limit <= volt <= high_limit else "NG"
                
                await v_node.write_value(volt)
                await r_node.write_value(result)
                await t_node.write_value(True)
                
                print(f"[PLC -> UA] {volt:.3f} V -> {result}")
            except Exception as e:
                print(" 통신 오류:", e)
                await asyncio.sleep(1)
                
                try:
                    await asyncio.to_thread(plc.close)
                except:
                    pass
                
                try:
                    await plc_connect()
                    print("PLC 재연결 성공")
                except Exception:
                    print("PLC 재연결 실패, 5초후 재시도")
                    await asyncio.sleep(5)
            await asyncio.sleep(1)
            
async def main():
    await plc_connect()
    print(f" PLC 연결 성공 ({PLC_IP}:{PLC_PORT})")
    await writer_loop()
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("종료합니다.")
        sys.exit(0)