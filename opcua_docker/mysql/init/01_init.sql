/* v6.2 bootstrap: create both DBs + app user + grants */

-- DB 생성 (실/더미 둘 다)
CREATE DATABASE IF NOT EXISTS secondary_battery_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE DATABASE IF NOT EXISTS secondary_battery_dummy_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- 애플리케이션 계정 (이미 있으면 통과)
CREATE USER IF NOT EXISTS 'root2'@'%' IDENTIFIED BY 'projectteam2@@';

-- 두 DB 모두 권한 부여
GRANT ALL PRIVILEGES ON secondary_battery_db.*       TO 'root2'@'%';
GRANT ALL PRIVILEGES ON secondary_battery_dummy_db.* TO 'root2'@'%';

FLUSH PRIVILEGES;