import time, os, mysql.connector
from dotenv import load_dotenv
load_dotenv("config.env")

DB = mysql.connector.connect(
    host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PW"),
    database=os.getenv("DB_NAME"), autocommit=True)
cur = DB.cursor()

SQL = """
INSERT INTO line_summary
  (line_id,work_date,total_output,total_defect,
   global_quality_rate,plan_down,unplan_down)
SELECT line_id,CURDATE(),
       SUM(daily_output),SUM(defect),
       (SUM(daily_output)-SUM(defect))/SUM(daily_output)*100,
       SUM(planne_downtime),SUM(unplanned_downtime)
  FROM process_production
 WHERE DATE(created_at)=CURDATE()
 GROUP BY line_id
ON DUPLICATE KEY UPDATE
  total_output=VALUES(total_output),
  total_defect=VALUES(total_defect),
  global_quality_rate=VALUES(global_quality_rate),
  plan_down=VALUES(plan_down),
  unplan_down=VALUES(unplan_down);
"""

while True:
    cur.execute(SQL)
    print("line_summary upsert complete")
    time.sleep(1800)          # 30분