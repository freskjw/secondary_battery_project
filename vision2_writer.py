import asyncio, sys
from asyncua import Client

UA = "opc.tcp://localhost:4840/inspect/server/"
inspect = "ns=2;s=InspectSystem/"

async def send(result:str):
    async with Client(UA) as cli:
        await cli.get_node(inspect + "Vision2Result").write_value(result.upper())
        await cli.get_node(inspect + "TriggerFlag").write_value(True)
        print(f"[Vision2] result = {result} 전송완료")
        
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법 : python vision2_writer.py <result(OK/NG)>")
        sys.exit(1)
    
    asyncio.run(send(sys.argv[1]))