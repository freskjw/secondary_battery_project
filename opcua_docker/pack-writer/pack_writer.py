# pack_writer.py  (async 버전 예시)
import os, asyncio, json, time
from asyncua import Client, ua
from lot_db_helper import get_conn_cursor

URL   = os.getenv("OPCUA_URL", "opc.tcp://opcua-server:4840/")
NODES = {
    "pack6_done":  "ns=2;s=Pack6Done",
    "pack8_done":  "ns=2;s=Pack8Done",
    #"voltage":     "ns=2;s=Pack_Voltage",
}

class Handler:
    async def datachange_notification(self, node, val, _):
        tag = next(k for k,v in NODES.items() if v==node.nodeid.to_string())
        if tag in ("pack6_done","pack8_done") and val:
            await insert_pack(tag)

async def insert_pack(tag):
    typ = "2x3" if tag=="pack6_done" else "2x4"
    async with get_conn_cursor() as (cnx,cur):
        cur.execute("SELECT measure_value FROM module_process_log "
                    "WHERE module_type=%s AND process_id='P03' "
                    "ORDER BY created_at DESC LIMIT 3", (typ,))
        voltages = [v[0] for v in cur.fetchall()]
        pack_v = sum(voltages)/len(voltages) if voltages else None
        cur.execute("""
            INSERT INTO pack_table(pack_type, pack_voltage)
            VALUES(%s,%s)
        """, (typ, pack_v))
        cnx.commit()

async def main():
    async with Client(URL) as client:
        handler = Handler()
        sub     = await client.create_subscription(100, handler)
        await asyncio.gather(
            *[sub.subscribe_data_change(client.get_node(n))   # get_node() 는 sync 메서드
              for n in NODES.values()]
        )

        print("▶ Pack-Writer ready — waiting for PLC signals")
        await asyncio.Future()   # run forever

if __name__ == "__main__":
    asyncio.run(main())