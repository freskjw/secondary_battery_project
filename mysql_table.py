import mysql.connector, os
from dotenv import load_dotenv

# .env에서 DB 설정 가져오기
load_dotenv("config.env")
DB = dict(
    host        = os.getenv("DB_HOST"),
    user        = os.getenv("DB_USER"),
    password    = os.getenv("DB_PW"),
    database    = os.getenv("DB_NAME"),
    port        = int(os.getenv("DB_PORT"))
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lot_tracker(
    module_type VARCHAR(10) PRIMARY KEY,
    last_serial INT NOT NULL
);
INSERT IGNORE INTO lot_tracker (module_type, last_serial)
VALUES ('2x3', 0), ('2x4', 0);

CREATE TABLE IF NOT EXISTS module_process_log(
    lot_no              VARCHAR(20) PRIMARY KEY,
    module_type         VARCHAR(10),
    angle               FLOAT,
    vision1_result      VARCHAR(20),
    vision1_timestamp   DATETIME,
    vision2_result      VARCHAR(20),
    vision2_timestamp   DATETIME,
    voltage             FLOAT,
    voltage_result      VARCHAR(10),
    voltage_timestamp   DATETIME
); """

def main():
    try:
        db = mysql.connector.connect(**DB)
        with db.cursor() as cur:
            for stmt in SCHEMA_SQL.split(";"):
                s = stmt.strip()
                if s:
                    cur.execute(s)
        db.commit()
        print(" 테이블 생성 / 초기화 완료")
    except mysql.connector.Error as e:
        print(" MySQL Error:", e)
    finally:
        db.close()
    
if __name__ == "__main__":
    main()