# vision2_writer.py
import asyncio, os, time
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua

load_dotenv("config.env")
PLC_IP=os.getenv("PLC_IP","192.168.3.30"); PLC_PORT=int(os.getenv("PLC_PORT","6001"))
UA_EP=os.getenv("UA_ENDPOINT","opc.tcp://opcua-server:4840/inspect/server/")
NS_URI=os.getenv("UA_NAMESPACE","http://inspect.system")
POLL=0.05

plc=Type3E(); plc.host,plc.port,plc.unit_code,plc.timeout=PLC_IP,PLC_PORT,0xFF,3
async def plc_connect():
    while True:
        try: await asyncio.to_thread(plc.connect,PLC_IP,PLC_PORT); return
        except: await asyncio.sleep(1)

async def read_bits():
    raw=await asyncio.to_thread(plc.batchread_bitunits,"M240",22)
    return {f"M{240+i}":bool(raw[i]) for i in range(22)}

async def main():
    await plc_connect()
    async with Client(UA_EP) as cli:
        idx=await cli.get_namespace_index(NS_URI)
        insp=await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        v2_node  =await insp.get_child([f"{idx}:Vision2Result"])
        flag_node=await insp.get_child([f"{idx}:TriggerFlag"])

        prev=False
        while True:
            b=await read_bits(); cap=b["M261"]
            if not prev and cap:
                result="OK" if b["M244"] else "NG"
                await v2_node.write_value(ua.Variant(result,ua.VariantType.String))
                await flag_node.write_value(ua.Variant(True,ua.VariantType.Boolean))
                print(f"[V2] {time.strftime('%H:%M:%S')}  result={result}")
            prev=cap; await asyncio.sleep(POLL)

if __name__=="__main__":
    asyncio.run(main())