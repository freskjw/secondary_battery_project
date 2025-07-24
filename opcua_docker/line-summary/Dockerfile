# line-summary/Dockerfile  (30 분마다 line_summary 집계)
FROM python:3.11-slim
WORKDIR /app

# requirements 재사용
COPY shared/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 집계 스크립트
COPY line-summary/summary_scheduler.py .

CMD ["python", "summary_scheduler.py"]