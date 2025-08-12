# v6 ★ PATCHED: P03 시작/완료 페어 트리거(armed) + 디바운스 + 공정로그 유지
import asyncio, os, sys, time, struct
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua
from lot_db_helper import get_next_lot, update_module, get_conn_cursor

load_dotenv("config.env")

# ── PLC / Threshold 설정
PLC_IP      = os.getenv("PLC_IP", "192.168.3.30")
PLC_PORT    = int(os.getenv("PLC_PORT", "6003"))
PLC_DEV     = os.getenv("PLC_DEVICE", "D100")     # 32-bit float (2 words, little-endian)

START_DEV   = os.getenv("VOLT_START_BIT", "M560") # 전압검사 시작 신호
DONE_DEV    = os.getenv("VOLT_DONE_BIT",  "M56")  # 전압검사 완료 신호

POLL        = float(os.getenv("V3_POLL", "0.05"))
DEBOUNCE_SEC= float(os.getenv("V3_DEBOUNCE", "0.20"))

LOW         = float(os.getenv("VOLT_LOW_LIMIT",  "7.7"))
HIGH        = float(os.getenv("VOLT_HIGH_LIMIT", "8.3"))

# ── OPC UA
UA_EP       = os.getenv("UA_ENDPOINT", "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI      = os.getenv("UA_NAMESPACE", "http://inspect.system")

# ── PLC 핸들
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

async def read_float():
    # D-word 2개(low, high) → little-endian float
    w = await asyncio.to_thread(plc.batchread_wordunits, PLC_DEV, 2)  # [low, high]
    raw = (w[1] << 16) | (w[0] & 0xFFFF)
    return struct.unpack('<f', raw.to_bytes(4, 'little'))[0]

async def read_bit(dev: str) -> bool:
    return bool((await asyncio.to_thread(plc.batchread_bitunits, dev, 1))[0])

async def main():
    await plc_connect()

    # ── 스타트업 세이프: 현재 상태로 prev_* 초기화 → 부팅 직후 가짜 트리거 방지
    prev_start = await read_bit(START_DEV)
    prev_done  = await read_bit(DONE_DEV)
    armed = False
    last_fire_ts = 0.0

    async with Client(UA_EP) as cli:
        idx       = await cli.get_namespace_index(NS_URI)
        insp      = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        volt_node = await insp.get_child([f"{idx}:Voltage"])
        res_node  = await insp.get_child([f"{idx}:VoltageResult"])
        flag_node = await insp.get_child([f"{idx}:TriggerFlag"])

        while True:
            start = await read_bit(START_DEV)
            done  = await read_bit(DONE_DEV)
            now   = time.monotonic()

            # 시작 상승엣지 → 무장
            if (not prev_start) and start:
                armed = True

            # 완료 상승엣지 + 무장 + 디바운스 → 측정/기록
            if armed and (not prev_done) and done and (now - last_fire_ts) >= DEBOUNCE_SEC:
                try:
                    volt = await read_float()
                except Exception as e:
                    print(f"[Volt] ⚠️ read_float error: {e}")
                    volt = float('nan')

                status = "OK" if (volt == volt) and (LOW <= volt <= HIGH) else "NG"  # NaN 대비

                lot = get_next_lot(stage=3)   # (P02 스크랩 제외 정책은 내부 함수에 따름)
                if lot is None:
                    print("[Volt] ℹ️ pending LOT not found (maybe scrapped at P02) — skip")
                else:
                    # DB 업데이트
                    update_module(
                        lot,
                        voltage=volt,
                        voltage_ok=1 if status == "OK" else 0,
                        stage3_done=1,
                    )
                    # 공정 로그(P03) 삽입: cp-calculator용
                    with get_conn_cursor() as (_, cur):
                        cur.execute("""
                            INSERT INTO module_process_log
                              (lot_no, module_type, process_id, measure_value, result, created_at)
                            VALUES (%s, %s, 'P03', %s, %s, NOW())
                        """, (lot, '2x3' if '6P' in lot else '2x4', volt, status))

                # OPC UA 갱신(모니터링/브릿지용)
                await volt_node.write_value(ua.Variant(volt, ua.VariantType.Float))
                await res_node.write_value(ua.Variant(status, ua.VariantType.String))
                await flag_node.write_value(ua.Variant(True, ua.VariantType.Boolean))

                print(f"[Volt] {time.strftime('%H:%M:%S')}  {lot or '--'}  {volt:6.3f} V → {status}")

                last_fire_ts = now
                armed = False  # 완료 처리 후 해제

            prev_start, prev_done = start, done
            await asyncio.sleep(POLL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)