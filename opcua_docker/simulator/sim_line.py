# simulator/sim_line.py  (retry+full cycle)
import asyncio, os, random, time
from asyncua import Client, ua

UA_EP  = os.getenv("UA_ENDPOINT","opc.tcp://opcua-server:4840/inspect/server/")
NS_URI = os.getenv("UA_NAMESPACE","http://inspect.system")
TARGET = int(os.getenv("SIM_TARGET","30"))
DELAY  = float(os.getenv("SIM_DELAY","3"))

PREFIX, serial = {"2x3":"6P","2x4":"8P"}, {"2x3":0,"2x4":0}
def next_lot(t): serial[t]+=1; return f"KCM-{PREFIX[t]}-{serial[t]:03d}"

async def connect_client():
    for i in range(30):                           # 최대 30 s 재시도
        try:
            cli = Client(UA_EP); await cli.connect(); return cli
        except Exception as e:
            print(f"[SIM] UA connect retry {i+1}/30 … {e}")
            await asyncio.sleep(1)
    raise RuntimeError("UA server not reachable")

async def toggle(node):   # TriggerFlag 토글
    await node.write_value(True);  await asyncio.sleep(0.05)
    await node.write_value(False)

async def main():
    async with await connect_client() as cli:
        idx  = await cli.get_namespace_index(NS_URI)
        insp = await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        n = {k: await insp.get_child([f"{idx}:{k}"]) for k in
             ["TargetOutput","StartFlag","TriggerFlag",
              "LotNo","Angle","Vision1Result","Vision2Result",
              "Voltage","VoltageResult"]}

        # Start
        await n["TargetOutput"].write_value(ua.Variant(TARGET, ua.VariantType.Int32))
        await n["StartFlag"].write_value(ua.Variant(True, ua.VariantType.Boolean))
        print(f"▶ SIM Start  target={TARGET}")
        await asyncio.sleep(1)

        # LOT 반복 (P01~P04)
        for _ in range(TARGET):
            mtype = random.choice(["2x3","2x4"]); lot = next_lot(mtype)

            ok1 = random.random()>0.1
            await n["LotNo"].write_value(lot)
            await n["Angle"].write_value(ua.Variant(0.0 if ok1 else 90.0, ua.VariantType.Float))
            await n["Vision1Result"].write_value("OK" if ok1 else "NG")
            await toggle(n["TriggerFlag"]); await asyncio.sleep(DELAY)

            ok2 = random.random()>0.1
            await n["Vision2Result"].write_value("OK" if ok2 else "NG")
            await toggle(n["TriggerFlag"]); await asyncio.sleep(DELAY)

            volt = round(random.uniform(3.75,4.15),3); ok3=3.9<=volt<=4.1
            await n["Voltage"].write_value(ua.Variant(volt,ua.VariantType.Float))
            await n["VoltageResult"].write_value("OK" if ok3 else "NG")
            await toggle(n["TriggerFlag"]); await asyncio.sleep(DELAY)

            await toggle(n["TriggerFlag"]); await asyncio.sleep(DELAY)  # P04

            print(f"[SIM] {lot}  V={volt:.3f}→{'OK' if ok3 else 'NG'}")
            await asyncio.sleep(random.uniform(0.2,0.6))

        # End
        await n["StartFlag"].write_value(ua.Variant(False, ua.VariantType.Boolean))
        print("■ SIM End")
if __name__=="__main__":
    asyncio.run(main())