import asyncio, sys
from asyncua import Client

UA = "opc.tcp://localhost:4840/inspect/server/"
inspect = "ns=2;s=InspectSystem/"

async def send(angle:float, result:str):
    async with Client(UA) as cli:
        await cli.get_node(inspect + "Angle").write_value(angle)
        await cli.get_node(inspect + "Vision1Result").write_value(result.upper())
        await cli.get_node(inspect + "TriggerFlag").write_value(True)
        print(f"[Vision1] angle = {angle}, result={result} 전송")
        
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법 : python vision1_writer.py <angle(float)> <result(OK/NG)>")
        sys.exit(1)
        
    a = float(sys.argv[1])
    r = sys.argv[2]
    asyncio.run(send(a,r))