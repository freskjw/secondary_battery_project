from dotenv import load_dotenv
import mysql.connector, os, datetime

load_dotenv("config.env")
DB_info= dict(
    host        = os.getenv("DB_HOST"),
    user        = os.getenv("DB_USER"),
    password    = os.getenv("DB_PW"),
    database    = os.getenv("DB_NAME")
)

def db_conn():
    return mysql.connector.connect(**DB_info)

def next_lot(cursor, mtype:str) -> str:
    prefix = {"2x3": "6P", "2x4": "8P"}[mtype]
    cursor.execute(
        "SELECT last_serial FROM lot_tracker WHERE module_type = %s",(mtype,)
        )
    next = cursor.fetchone()[0] + 1
    cursor.execute(
        "UPDATE lot_tracker SET last_serial = %s WHERE module_type = %s",(next,mtype)
    )
    return f"KCM-{prefix}-{next:03d}"

def insert_vision1(cur, module_type, angle, result):
    lot = next_lot(cur, module_type)
    
    sql = """
    INSERT INTO module_process_log(
            lot_no, module_type, angle, vision1_result, vision1_timestamp
        ) VALUES (%s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
        angle               = VALUES(angle),
        vision1_result      = VALUES(vision1_result),
        vision1_timestamp   = NOW()
    """
    cur.execute(sql, (lot, module_type, angle, result))
    return lot

def update_vision2(lot, result, cur):
    sql = """
    UPDATE module_process_log
        SET vision2_result      = %s, 
            vision2_timestamp   = NOW()
        WHERE lot_no = %s
    """
    cur.execute(sql, (result, lot))
    
def update_voltage(lot, volt, result, cur):
    sql = """
    UPDATE module_process_log
        SET voltage             = %s,
            voltage_result      = %s,
            voltage_timestamp   = NOW()
        WHERE lot_no        = %s
    """
    
    cur.execute(sql, (volt, result, lot))