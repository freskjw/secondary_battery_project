# v6 ★ PATCHED: 부팅 직후 가짜 트리거 방지 + 디바운스 + M277 명시 분기
import asyncio, os, time
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua
from lot_db_helper import get_next_lot, get_conn_cursor, update_module

load_dotenv("config.env")
PLC_IP   = os.getenv("PLC_IP",   "192.168.3.30")
PLC_PORT = int(os.getenv("PLC_PORT", "6004"))
UA_EP    = os.getenv("UA_ENDPOINT", "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI   = os.getenv("UA_NAMESPACE", "http://inspect.system")

POLL          = 0.05
DEBOUNCE_SEC  = 0.20   # 짧은 깜빡임/노이즈 중복 방지

plc = Type3E()
plc.host, plc.port, plc.unit_code, plc.timeout = PLC_IP, PLC_PORT, 0xFF, 3

async def plc_connect():
    retry = 0
    while True:
        try:
            await asyncio.to_thread(plc.connect, PLC_IP, PLC_PORT)
            print(f" PLC connected ({PLC_IP}:{PLC_PORT})")
            return
        except Exception as e:
            retry += 1
            print(f" PLC connect failed, retry {retry}: {e}")
            await asyncio.sleep(1)

async def read_bits():
    # M240~M279
    raw = await asyncio.to_thread(plc.batchread_bitunits, "M240", 40)
    return {f"M{240+i}": bool(raw[i]) for i in range(40)}

def v2_result_from_bits(b) -> str:
    # 명시 분기: OK(M275) / Missing(M276) / Misinsert(M277)
    if b.get("M275", False):
        return "OK"
    elif b.get("M276", False):
        return "NG(Missing)"
    elif b.get("M277", False):
        return "NG(Misinsert)"
    else:
        return "NG(Unknown)"   # 안전한 기본값(분류 불가)

async def main():
    await plc_connect()

    # 시작 시 현재 상태로 prev270 초기화 → 부팅 직후 M270=1이면 첫 루프 트리거 방지
    first_bits = await read_bits()
    prev270 = first_bits.get("M270", False)
    last_fire_ts = 0.0

    async with Client(UA_EP) as cli:
        idx  = await cli.get_namespace_index(NS_URI)
        insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        v2_node   = await insp.get_child([f"{idx}:Vision2Result"])
        flag_node = await insp.get_child([f"{idx}:TriggerFlag"])

        while True:
            b = await read_bits()
            trig = b.get("M270", False)
            now  = time.monotonic()

            # 상승엣지 + 디바운스
            if (not prev270) and trig and (now - last_fire_ts) >= DEBOUNCE_SEC:
                lot = get_next_lot(stage=2)
                if lot is None:
                    print("[V2] ⚠️ no pending LOT — skip")
                else:
                    result = v2_result_from_bits(b)

                    # OPC UA 업데이트
                    await v2_node.write_value(ua.Variant(result, ua.VariantType.String))
                    await flag_node.write_value(ua.Variant(True,  ua.VariantType.Boolean))

                    # DB 업데이트
                    if result == "OK":
                        update_module(lot, v2_result=result, v2_ok=1, stage2_done=1)
                    else:
                        reason = 'Misinsert' if 'Misinsert' in result else ('Missing' if 'Missing' in result else 'Unknown')
                        with get_conn_cursor() as (_, cur):
                            cur.execute("""
                                UPDATE module
                                   SET v2_result=%s,
                                       v2_ok=0,
                                       stage2_done=1,
                                       is_scrap=1,
                                       scrap_stage='P02',
                                       scrap_reason=%s,
                                       scrap_at=NOW()
                                 WHERE lot_no=%s
                            """, (result, reason, lot))

                    print(f"[V2] {time.strftime('%H:%M:%S')}  {lot}  {result}")

                last_fire_ts = now

            prev270 = trig
            await asyncio.sleep(POLL)

if __name__ == "__main__":
    asyncio.run(main())