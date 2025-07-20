import asyncio, os
from asyncua import Client
from lot_db_helper import db_conn, insert_vision1, update_vision2, update_voltage

UA = "opc.tcp://localhost:4840/inspect/server/"

async def main():
    async with Client(UA) as cli:
        inspect = "ns=2;s=InspectSystem/"
        nodes = {k : cli.get_node(inspect + k) for k in
                 ["TriggerFlag", "Angle", "Vision1Result", "Vision2Result", "Voltage", "VoltageResult"]}
        prev = False
        lot = None
        while True:
            trg = await nodes["TriggerFlag"].read_value()
            if not prev and trg:
                angle = await nodes["Angle"].read_value()
                v1    = await nodes["Vision1Result"].read_value()
                v2    = await nodes["Vision2Result"].read_value()
                volt  = await nodes["Voltage"].read_value()
                vr    = await nodes["VoltageResult"].read_value()
                
                db = db_conn(); cur = db.cursor()
                if v1:
                    mtype = "2x3" if "6P" in v1 else "2x4"
                    lot = insert_vision1(cur,mtype,angle,v1)
                if v2 and lot:
                    update_vision2(cur,lot,v2)
                if volt and lot:
                    update_voltage(cur,lot,volt,vr)
                db.commit()
                cur.close()
                db.close()
                
                await nodes["TriggerFlag"].write_value(False)
            prev = trg
            await asyncio.sleep(0.1)
            
if __name__ == "__main__":
    asyncio.run(main())