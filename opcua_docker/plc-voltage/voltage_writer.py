import asyncio, os, sys, time, struct
from dotenv import load_dotenv
from pymcprotocol import Type3E
from asyncua import Client, ua

load_dotenv("config.env")
PLC_IP=os.getenv("PLC_IP","192.168.3.30"); PLC_PORT=int(os.getenv("PLC_PORT","6001"))
PLC_DEV=os.getenv("PLC_DEVICE","D200"); POLL=0.05
UA_EP =os.getenv("UA_ENDPOINT","opc.tcp://opcua-server:4840/inspect/server/")
NS_URI=os.getenv("UA_NAMESPACE","http://inspect.system")
LOW=float(os.getenv("VOLT_LOW_LIMIT","3.70")); HIGH=float(os.getenv("VOLT_HIGH_LIMIT","4.20"))

plc=Type3E(); plc.host,plc.port,plc.unit_code,plc.timeout=PLC_IP,PLC_PORT,0xFF,3
async def plc_connect():
    while True:
        try: await asyncio.to_thread(plc.connect,PLC_IP,PLC_PORT); return
        except: await asyncio.sleep(1)

async def read_float():
    w=await asyncio.to_thread(plc.batchread_wordunits,PLC_DEV,2)
    raw=(w[1]<<16)|(w[0]&0xFFFF)
    return struct.unpack('<f',raw.to_bytes(4,'little'))[0]
async def read_m300(): return bool((await asyncio.to_thread(plc.batchread_bitunits,"M300",1))[0])

async def main():
    await plc_connect()
    async with Client(UA_EP) as cli:
        idx=await cli.get_namespace_index(NS_URI)
        insp=await cli.nodes.objects.get_child([f"{idx}:InspectSystem"])
        v_node  =await insp.get_child([f"{idx}:Voltage"])
        res_node=await insp.get_child([f"{idx}:VoltageResult"])
        flag_node=await insp.get_child([f"{idx}:TriggerFlag"])

        prev=False
        while True:
            trig=await read_m300()
            if not prev and trig:
                volt=await read_float()
                status="OK" if LOW<=volt<=HIGH else "NG"
                await v_node .write_value(ua.Variant(volt,ua.VariantType.Float))
                await res_node.write_value(ua.Variant(status,ua.VariantType.String))
                await flag_node.write_value(ua.Variant(True,ua.VariantType.Boolean))
                print(f"[Volt] {time.strftime('%H:%M:%S')}  {volt:6.3f} V → {status}")
            prev=trig; await asyncio.sleep(POLL)

if __name__=="__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: sys.exit(0)