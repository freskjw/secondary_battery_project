> 목적: 실제 공정 데이터가 적을 때 **더미 DB**로 리포트를 생성하고, 이후 **실제 DB**로 무중단 전환하기.

## 1) 구성 개요
- **실제(프로덕션) DB**: `secondary_battery_db`
- **더미(테스트) DB**: `secondary_battery_dummy_db`
- **ai-reporter의 DB 선택 규칙**
  - `REPORT_DB_*` 환경변수가 설정되어 있으면 그것을 사용
  - 설정되어 있지 않으면 `DB_*` 값(실제 DB)으로 **자동 폴백**
- 리포트 산출물
  - HTML 파일: `./reports/report_YYYY-MM-DD_<audience>.html`
  - DB 보관: 연결된 DB의 `report_archive` 테이블에 저장(= 더미 사용 시 더미 DB에 저장)

## 2) 더미 DB 준비(최초 1회)
1. 더미 스키마 생성(SQL 파일: `db/init/020_dummy_schema.sql`)
   ```bash
   docker exec -i opcua_docker-mysql-1 \
     mysql -h 127.0.0.1 -uroot -p${DB_PW} < db/init/020_dummy_schema.sql
   ```
2. (선택) 더미 데이터 적재: `dummy-seeder` 서비스 실행
   ```bash
   docker compose up -d --build dummy-seeder
   docker logs -f dummy-seeder
   ```
   - 파라미터: `DUMMY_DAYS`, `DUMMY_PER_DAY`, `DUMMY_VOLT_MEAN/STD`, `DUMMY_VOLT_NG_RATE`, `DUMMY_VISION_NG_RATE`

## 3) 더미 DB로 리포터 실행(테스트 모드)
1. `config.env`에 아래를 추가/수정
   ```env
   # Reporter 전용 DB(더미)
   REPORT_DB_HOST=
   REPORT_DB_PORT=
   REPORT_DB_USER=
   REPORT_DB_PW=
   REPORT_DB_NAME=secondary_battery_dummy_db
   ```
   > HOST/USER/PW를 비워두면 컨테이너 내부에서 같은 MySQL을 사용하며, 포트/권한이 기본값이면 생략 가능.

2. ai-reporter 기동 & 즉시 테스트 실행
   ```bash
   docker compose up -d --build ai-reporter
   docker exec -it ai-reporter python - <<'PY'
   import reporter; reporter.run_once()
   PY
   ```
3. 결과 확인
   ```bash
   ls -1 reports/ | tail -n 3
   docker exec -i opcua_docker-mysql-1 mysql -uroot -p${DB_PW} -e \
     "SELECT report_date,audience,LENGTH(html) FROM secondary_battery_dummy_db.report_archive ORDER BY id DESC LIMIT 3;"
   ```

## 4) 실제 DB로 전환(Dummy → Prod)
**옵션 A: 폴백 사용(권장, 가장 간단)**
1. `config.env`에서 `REPORT_DB_*` 항목을 **모두 비우거나 제거**
2. 리포터 재시작
   ```bash
   docker compose up -d ai-reporter
   ```
3. 리포트가 실제 DB(`secondary_battery_db.report_archive`)에 쌓이는지 확인
   ```bash
   docker exec -i opcua_docker-mysql-1 mysql -uroot -p${DB_PW} -e \
     "SELECT report_date,audience,LENGTH(html) FROM secondary_battery_db.report_archive ORDER BY id DESC LIMIT 3;"
   ```

**옵션 B: 명시적 지정**
1. `config.env`에 실제 DB를 명시적으로 설정
   ```env
   REPORT_DB_HOST=${DB_HOST}
   REPORT_DB_PORT=${DB_PORT}
   REPORT_DB_USER=${DB_USER}
   REPORT_DB_PW=${DB_PW}
   REPORT_DB_NAME=${DB_NAME}
   ```
2. 리포터 재시작(동일)

## 5) 전환 체크리스트
- [ ] 두 DB 모두 **010~016 스키마**가 존재하는지 확인(특히 `report_archive`, `vw_spec_active`, `kpi_target`)
  ```sql
  USE secondary_battery_db;        SHOW FULL TABLES LIKE 'report_archive';
  USE secondary_battery_dummy_db;  SHOW FULL TABLES LIKE 'report_archive';
  ```
- [ ] 타임존: `Asia/Seoul` 그대로인지(`REPORT_RUN_AT` 기준 시간 확인)
- [ ] `reports/` 디렉토리에 날짜별 HTML 생성 확인
- [ ] ai-reporter 로그에 연결 DB 정보가 기대와 일치
- [ ] (선택) 더미→실제 전환 시 더미 DB의 과거 리포트 이관 필요 여부 검토

## 6) 주의사항 / 팁
- 리포트 보관 위치(DB)는 **연결된 DB**입니다. 더미 사용 기간동안 생성된 리포트가 더미 DB에 저장됩니다.
  - 필요 시 이관:
    ```sql
    INSERT IGNORE INTO secondary_battery_db.report_archive
    SELECT * FROM secondary_battery_dummy_db.report_archive;
    ```
- ai-reporter는 읽기/쓰기 모두 단일 커넥션을 사용합니다. 전환 직후 첫 실행에서 대상 DB가 맞는지 꼭 확인하세요.
- MySQL 8.0+ 권장(`CREATE OR REPLACE VIEW`, `IF NOT EXISTS` 구문 사용).

## 7) 변경 이력(README)
- **2025-08-12**: Dummy DB → 실제 DB 전환 가이드 추가. 앞으로 코드 수정 시 이 README를 **항상 함께 갱신**합니다.


---- 리포트는 KST 08:15 기준으로 실행되는데 아래 코드로 바로 실행 가능 ----
docker exec -it ai-reporter python - <<'PY'
import reporter; reporter.run_once()
PY
