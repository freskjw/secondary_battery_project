# 베이스 이미지
FROM python:3.11-slim

# 작업 디렉토리 생성
WORKDIR /app

# 의존성 복사 및 설치
COPY shared/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 코드 복사
COPY opcua-server/opcua_server.py .

# healthcheck 스크립트 추가
COPY healthcheck/ua_ping.py /healthcheck/ua_ping.py

# 실행 명령
CMD ["python", "opcua_server.py"]