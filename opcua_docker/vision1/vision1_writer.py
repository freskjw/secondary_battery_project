# vision1_writer.py
import asyncio, os, time
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua

# ───── 1) 설정
load_dotenv("config.env")
PLC_IP=os.getenv("PLC_IP","192.168.3.30"); PLC_PORT=int(os.getenv("PLC_PORT","6001"))
UA_EP =os.getenv("UA_ENDPOINT","opc.tcp://opcua-server:4840/inspect/server/")
NS_URI=os.getenv("UA_NAMESPACE","http://inspect.system")
POLL  =0.05

# LOT 번호 생성(내부 카운터)
PREFIX={"2x3":"6P","2x4":"8P"}; serial={"2x3":0,"2x4":0}
def next_lot(t): serial[t]+=1; return f"KCM-{PREFIX[t]}-{serial[t]:03d}"

# ───── 2) PLC 객체
plc=Type3E(); plc.host,plc.port,plc.unit_code,plc.timeout=PLC_IP,PLC_PORT,0xFF,3
async def plc_connect():
    while True:
        try: await asyncio.to_thread(plc.connect,PLC_IP,PLC_PORT); return
        except: await asyncio.sleep(1)

async def read_bits():
    raw=await asyncio.to_thread(plc.batchread_bitunits,"M240",22)  # M240~M261
    return {f"M{240+i}":bool(raw[i]) for i in range(22)}

# ───── 3) 메인
async def main():
    await plc_connect()
    async with Client(UA_EP) as cli:
        idx=await cli.get_namespace_index(NS_URI)
        insp=await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        lot_node =await insp.get_child([f"{idx}:LotNo"])
        ang_node =await insp.get_child([f"{idx}:Angle"])
        v1_node  =await insp.get_child([f"{idx}:Vision1Result"])
        flag_node=await insp.get_child([f"{idx}:TriggerFlag"])

        prev=False
        while True:
            b=await read_bits(); cap=b["M261"]
            if not prev and cap:                      # M261 상승에지
                mtype="2x3" if b["M240"] else "2x4"
                angle,result = (0.0,"OK") if b["M242"] else (90.0,"NG")
                lot=next_lot(mtype)

                await lot_node.write_value(ua.Variant(lot,ua.VariantType.String))
                await ang_node.write_value(ua.Variant(angle,ua.VariantType.Float))
                await v1_node .write_value(ua.Variant(result,ua.VariantType.String))
                await flag_node.write_value(ua.Variant(True,ua.VariantType.Boolean))

                print(f"[V1] {time.strftime('%H:%M:%S')} {lot}  angle={angle:.0f}° → {result}")
            prev=cap; await asyncio.sleep(POLL)

if __name__=="__main__":
    asyncio.run(main())