# vision1_writer.py  (rev.2025-07-30)
import asyncio, os, time
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua

from lot_db_helper import create_module_lot, update_module

# ───── 1) 설정
load_dotenv("config.env")
PLC_IP   = os.getenv("PLC_IP", "192.168.3.30")
PLC_PORT = int(os.getenv("PLC_PORT", "6001"))
UA_EP    = os.getenv("UA_ENDPOINT",
                     "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI   = os.getenv("UA_NAMESPACE", "http://inspect.system")
POLL     = 0.05

# ───── 2) PLC 객체
plc = Type3E()
plc.host, plc.port, plc.unit_code, plc.timeout = PLC_IP, PLC_PORT, 0xFF, 3


async def plc_connect():
    while True:
        try:
            await asyncio.to_thread(plc.connect, PLC_IP, PLC_PORT)
            return
        except Exception:
            await asyncio.sleep(1)


async def read_bits():
    raw = await asyncio.to_thread(plc.batchread_bitunits, "M240", 22)  # M240~M261
    return {f"M{240+i}": bool(raw[i]) for i in range(22)}


# ───── 3) 메인
async def main():
    await plc_connect()

    async with Client(UA_EP) as cli:
        idx = await cli.get_namespace_index(NS_URI)
        insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])

        lot_node  = await insp.get_child([f"{idx}:LotNo"])
        ang_node  = await insp.get_child([f"{idx}:Angle"])
        v1_node   = await insp.get_child([f"{idx}:Vision1Result"])
        flag_node = await insp.get_child([f"{idx}:TriggerFlag"])

        prev_cap = False
        while True:
            b = await read_bits()
            cap = b["M261"]                   # 촬영 완료 신호

            if not prev_cap and cap:          # 상승에지
                p_type = "6P" if b["M240"] else "8P"
                angle_ok = b["M242"]          # 0° OK / 90° NG
                angle, result = (0.0, "OK") if angle_ok else (90.0, "NG")

                lot = create_module_lot(p_type)

                # OPC UA 전달
                await lot_node.write_value(ua.Variant(lot, ua.VariantType.String))
                await ang_node.write_value(ua.Variant(angle, ua.VariantType.Float))
                await v1_node.write_value(ua.Variant(result,
                                                     ua.VariantType.String))
                await flag_node.write_value(ua.Variant(True,
                                                       ua.VariantType.Boolean))

                # DB 업데이트
                update_module(
                    lot,
                    v1_angle=angle,
                    v1_ok=1 if result == "OK" else 0,
                    stage1_done=1,
                )

                print(f"[V1] {time.strftime('%H:%M:%S')}  {lot}  "
                      f"angle={angle:.0f}° → {result}")

            prev_cap = cap
            await asyncio.sleep(POLL)


if __name__ == "__main__":
    asyncio.run(main())