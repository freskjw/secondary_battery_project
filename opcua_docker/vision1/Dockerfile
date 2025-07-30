# 도커파일
FROM python:3.11-slim
WORKDIR /app

COPY shared/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/lot_db_helper.py ./lot_db_helper.py
COPY vision1/vision1_writer.py .

CMD ["python", "vision1_writer.py"]