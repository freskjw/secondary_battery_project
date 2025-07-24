"""
sim_line.py  –  PLC 없는 환경 통합 테스트
──────────────────────────────────────
● UA TargetOutput / StartFlag → line_run 생성
● LOT / Angle / Vision2 / Voltage 시퀀스 → Writer·Bridge·DB 흐름 검증
"""
import asyncio, os, random, time
from asyncua import Client, ua

UA_EP   = os.getenv("UA_ENDPOINT",  "opc.tcp://opcua-server:4840/inspect/server/")
NS_URI  = os.getenv("UA_NAMESPACE", "http://inspect.system")
TARGET  = int(os.getenv("SIM_TARGET", "8"))        # 목표 생산량
DELAY   = float(os.getenv("SIM_DELAY", "0.4"))     # 공정 간 지연(s)

PREFIX  = {"2x3": "6P", "2x4": "8P"}
serial  = {"2x3": 0, "2x4": 0}
def next_lot(t): serial[t]+=1; return f"KCM-{PREFIX[t]}-{serial[t]:03d}"

async def main():
    async with Client(UA_EP) as cli:
        idx  = await cli.get_namespace_index(NS_URI)
        insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])

        nodes = {k: await insp.get_child([f"{idx}:{k}"]) for k in
                 ["TargetOutput","StartFlag","LotNo","Angle","Vision1Result",
                  "Vision2Result","Voltage","VoltageResult","TriggerFlag"]}

        # 1) 목표생산량 + StartFlag
        await nodes["TargetOutput"].write_value(ua.Variant(TARGET, ua.VariantType.Int32))
        await nodes["StartFlag"]  .write_value(ua.Variant(True,   ua.VariantType.Boolean))
        print(f"▶ 시뮬레이터: StartFlag=TRUE, Target={TARGET}")

        await asyncio.sleep(1)                      # Bridge가 line_run 만들 시간

        # 2) ‘TARGET’ 개 LOT 생성
        for i in range(1, TARGET+1):
            mtype = random.choice(["2x3","2x4"])
            lot   = next_lot(mtype)

            # Vision-1 (P01)
            angle_ok = random.random() > 0.1
            await nodes["LotNo"].write_value(ua.Variant(lot, ua.VariantType.String))
            await nodes["Angle"].write_value(
                    ua.Variant(0.0 if angle_ok else 90.0, ua.VariantType.Float))
            await nodes["Vision1Result"].write_value(
                    ua.Variant("OK" if angle_ok else "NG", ua.VariantType.String))
            await nodes["TriggerFlag"].write_value(True)   # Bridge picks up
            await asyncio.sleep(DELAY)
            await nodes["TriggerFlag"].write_value(False)

            # Vision-2 (P02)
            v2_ok = random.random() > 0.1
            await nodes["Vision2Result"].write_value(
                    ua.Variant("OK" if v2_ok else "NG", ua.VariantType.String))
            await nodes["TriggerFlag"].write_value(True)
            await asyncio.sleep(DELAY)
            await nodes["TriggerFlag"].write_value(False)

            # Voltage (P03)
            volt = round(random.uniform(3.75, 4.15), 3)
            ok   = 3.70 <= volt <= 4.20
            await nodes["Voltage"].write_value(
                    ua.Variant(volt, ua.VariantType.Float))
            await nodes["VoltageResult"].write_value(
                    ua.Variant("OK" if ok else "NG", ua.VariantType.String))
            await nodes["TriggerFlag"].write_value(True)
            await asyncio.sleep(DELAY)
            await nodes["TriggerFlag"].write_value(False)

            print(f"[SIM] {lot}  v={volt:.3f}→{'OK' if ok else 'NG'}")

            await asyncio.sleep(random.uniform(0.2, 0.6))   # takt 편차

        # 3) 목표 달성 후 Stop
        await asyncio.sleep(1)
        await nodes["StartFlag"].write_value(ua.Variant(False, ua.VariantType.Boolean))
        print("■ 시뮬레이터 종료: StartFlag=FALSE")

if __name__ == "__main__":
    asyncio.run(main())
