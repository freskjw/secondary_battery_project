# voltage_writer.py  (rev.2025-07-31)
import asyncio, os, sys, time, struct
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua

from lot_db_helper import get_next_lot, update_module

load_dotenv("config.env")

PLC_IP     = os.getenv("PLC_IP", "192.168.3.30")
PLC_PORT   = int(os.getenv("PLC_PORT", "6001"))
PLC_DEV    = os.getenv("PLC_DEVICE", "D200")      # 전압값이 저장된 D-레지스터
POLL       = 0.05

UA_EP      = os.getenv("UA_ENDPOINT",
                       "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI     = os.getenv("UA_NAMESPACE", "http://inspect.system")

LOW        = float(os.getenv("VOLT_LOW_LIMIT",  "3.70"))
HIGH       = float(os.getenv("VOLT_HIGH_LIMIT", "4.20"))

plc = Type3E()
plc.host, plc.port, plc.unit_code, plc.timeout = PLC_IP, PLC_PORT, 0xFF, 3


async def plc_connect():
    while True:
        try:
            await asyncio.to_thread(plc.connect, PLC_IP, PLC_PORT)
            return
        except Exception:
            await asyncio.sleep(1)


async def read_float():
    w = await asyncio.to_thread(plc.batchread_wordunits, PLC_DEV, 2)
    raw = (w[1] << 16) | (w[0] & 0xFFFF)
    return struct.unpack('<f', raw.to_bytes(4, 'little'))[0]


async def read_m572():
    return bool((await asyncio.to_thread(plc.batchread_bitunits,
                                         "M572", 1))[0])   # 전압검사 완료 신호


async def main():
    await plc_connect()

    async with Client(UA_EP) as cli:
        idx       = await cli.get_namespace_index(NS_URI)
        insp      = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        volt_node = await insp.get_child([f"{idx}:Voltage"])
        res_node  = await insp.get_child([f"{idx}:VoltageResult"])
        flag_node = await insp.get_child([f"{idx}:TriggerFlag"])

        prev = False
        while True:
            trig = await read_m572()
            if not prev and trig:
                volt   = await read_float()
                status = "OK" if LOW <= volt <= HIGH else "NG"

                # ─ DB 큐에서 “전압 미처리 LOT” 1개
                lot = get_next_lot(stage=3)
                if lot is None:
                    print("[Volt] ⚠️ 대기 LOT 없음 — skip")
                else:
                    update_module(lot,
                                  voltage=volt,
                                  voltage_ok=1 if status == "OK" else 0,
                                  stage3_done=1)

                # OPC UA 디버그용
                await volt_node.write_value(ua.Variant(volt,
                                                       ua.VariantType.Float))
                await res_node.write_value(ua.Variant(status,
                                                      ua.VariantType.String))
                await flag_node.write_value(ua.Variant(True,
                                                       ua.VariantType.Boolean))

                print(f"[Volt] {time.strftime('%H:%M:%S')}  "
                      f"{lot or '--'}  {volt:6.3f} V → {status}")

            prev = trig
            await asyncio.sleep(POLL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)