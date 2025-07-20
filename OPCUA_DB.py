import mysql.connector
from asyncua import Client
import asyncio

async def db_upload():
    client = Client("opc.tcp://localhost:4840/vision/server/")
    await client.connect()
    
    angle = client.get_node("ns=2; s=VisionSystem/Angle")
    result = client.get_node("ns=2; s=VisionSystem/Result")
    module = client.get_node("ns=2; s=VisionSystem/ModuleType")
    trigger = client.get_node("ns=2; s=VisionSystem/TriggerFlag")
    
    db = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "projectteam2@@",
        database = "secondary_battery_db"
    )
    cursor = db.cursor()
    
    prev_trigger = False
    
    while True:
        curr_trigger = await trigger.read_value()
        
        if not prev_trigger and curr_trigger:
            val_angle = await angle.read_value()
            val_result = await result.read_value()
            val_module = await module.read_value()
            
            cursor.execute(
                "INSERT INTO vision_results (angle, result, module_type, timestamp) VALUSES (%s, %s, %s, NOW())",
                (val_angle, val_result, val_module)
            )
            db.commit()
            print(" DB 저장완료")
            
            await trigger.write_value(False)
            
        prev_trigger = curr_trigger
        await asyncio.sleep(0.1)
        
    await client.disconnect()
    
if __name__ == "__main__":
    asyncio.run(db_upload())