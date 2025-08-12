# vision1_writer.py  (v6.2)
# - M260(시작)/M261(완료) 페어
# - 타입: 배타적 샘플 다수결
# - 각도: M242 구간 샘플링 → 꼬리 안정성→다수결(동수=마지막) 결정
# - 디바운스/스타트업 세이프

import asyncio, os, time
from collections import deque, Counter
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua
from lot_db_helper import create_module_lot, update_module

load_dotenv("config.env")

PLC_IP   = os.getenv("PLC_IP", "192.168.3.30")
PLC_PORT = int(os.getenv("PLC_PORT", "6007"))

UA_EP    = os.getenv("UA_ENDPOINT", "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI   = os.getenv("UA_NAMESPACE", "http://inspect.system")

POLL         = float(os.getenv("V1_POLL", "0.05"))
DEBOUNCE_SEC = float(os.getenv("V1_DEBOUNCE", "0.20"))

# Angle 관련 옵션
ANGLE_OK_HIGH      = (os.getenv("V1_ANGLE_OK_HIGH", "1") == "1")  # True면 M242=1이 OK
ANGLE_TAIL_STABLE  = int(os.getenv("V1_ANGLE_TAIL_STABLE", "3"))   # 마지막 N개가 동일하면 그 값을 신뢰
ANGLE_OK_DEG       = float(os.getenv("V1_ANGLE_OK_DEG", "0"))
ANGLE_NG_DEG       = float(os.getenv("V1_ANGLE_NG_DEG", "90"))

# 읽기 범위: M240(6P), M241(8P), M242(AngleOK), M260(Start), M261(Done)
READ_BASE = "M240"
READ_LEN  = 22

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
    raw = await asyncio.to_thread(plc.batchread_bitunits, READ_BASE, READ_LEN)
    return {f"M{240+i}": bool(raw[i]) for i in range(READ_LEN)}

def xor_type(m6: bool, m8: bool):
    return "6P" if (m6 ^ m8 and m6) else ("8P" if (m6 ^ m8 and m8) else None)

def normalize_angle_ok(aok_raw: bool) -> bool:
    # 극성 조정: ANGLE_OK_HIGH=False면 의미 반전
    return aok_raw if ANGLE_OK_HIGH else (not aok_raw)

def decide_angle(samples: list[bool]) -> bool | None:
    """샘플 리스트(True=OK, False=NG). None=결정불가"""
    if not samples:
        return None
    # 꼬리 안정성: 마지막 N개가 모두 동일하면 그 값을 우선 채택
    if ANGLE_TAIL_STABLE > 0 and len(samples) >= ANGLE_TAIL_STABLE:
        tail = samples[-ANGLE_TAIL_STABLE:]
        if all(v is True for v in tail):
            return True
        if all(v is False for v in tail):
            return False
    # 다수결
    t = sum(1 for v in samples if v)
    f = len(samples) - t
    if t > f:
        return True
    if f > t:
        return False
    # 동수면 마지막 샘플
    return samples[-1]

async def main():
    await plc_connect()

    init = await read_bits()
    prev_start = init.get("M260", False)
    prev_done  = init.get("M261", False)

    armed = False
    last_fire_ts = 0.0

    type_samples  = deque()  # '6P'/'8P'
    angle_samples = deque()  # True(OK)/False(NG), normalized

    async with Client(UA_EP) as cli:
        idx = await cli.get_namespace_index(NS_URI)
        insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        lot_node  = await insp.get_child([f"{idx}:LotNo"])
        ang_node  = await insp.get_child([f"{idx}:Angle"])
        v1_node   = await insp.get_child([f"{idx}:Vision1Result"])
        flag_node = await insp.get_child([f"{idx}:TriggerFlag"])

        while True:
            b = await read_bits()
            m6   = b.get("M240", False)
            m8   = b.get("M241", False)
            aok  = b.get("M242", False)
            start= b.get("M260", False)
            done = b.get("M261", False)
            now  = time.monotonic()

            # 시작 상승엣지 → 무장 및 버퍼 초기화
            if (not prev_start) and start:
                armed = True
                type_samples.clear()
                angle_samples.clear()
                print(f"[V1] ▶ 시작 (M240={int(m6)} M241={int(m8)} M242={int(aok)})")

            # 무장 상태에서 지속 수집
            if armed:
                t = xor_type(m6, m8)
                if t:
                    type_samples.append(t)
                angle_samples.append(normalize_angle_ok(aok))

            # 완료 상승엣지 + 무장 + 디바운스 → 판단/기록
            if armed and (not prev_done) and done and (now - last_fire_ts) >= DEBOUNCE_SEC:
                # 타입 결정: 다수결(동수면 마지막)
                p_type = None
                if type_samples:
                    c = Counter(type_samples)
                    if c["6P"] > c["8P"]:
                        p_type = "6P"
                    elif c["8P"] > c["6P"]:
                        p_type = "8P"
                    else:
                        p_type = type_samples[-1]
                if not p_type:
                    print(f"[V1] ⚠ 타입 미확정 → LOT 스킵 (samples={list(type_samples)})")
                else:
                    # 각도 결정
                    angle_ok = decide_angle(list(angle_samples))
                    if angle_ok is None:
                        print(f"[V1] ⚠ 각도 미확정 → LOT 스킵 (angle_samples={list(angle_samples)})")
                    else:
                        angle  = ANGLE_OK_DEG if angle_ok else ANGLE_NG_DEG
                        result = "OK" if angle_ok else "NG"

                        lot = create_module_lot(p_type)

                        # OPC UA
                        await lot_node.write_value(ua.Variant(lot, ua.VariantType.String))
                        await ang_node.write_value(ua.Variant(angle, ua.VariantType.Float))
                        await v1_node.write_value(ua.Variant(result, ua.VariantType.String))
                        await flag_node.write_value(ua.Variant(True, ua.VariantType.Boolean))

                        # DB
                        update_module(
                            lot,
                            v1_angle=angle,
                            v1_ok=1 if result == "OK" else 0,
                            stage1_done=1,
                        )

                        print(f"[V1] {time.strftime('%H:%M:%S')}  {lot}  type={p_type}  "
                              f"type_samples={list(type_samples)}  "
                              f"angle_samples={list(angle_samples)[-min(8,len(angle_samples)):]}"
                              f"  angle={angle:.0f}° → {result}")

                # 리셋
                last_fire_ts = now
                armed = False
                type_samples.clear()
                angle_samples.clear()

            prev_start, prev_done = start, done
            await asyncio.sleep(POLL)

if __name__ == "__main__":
    asyncio.run(main())
