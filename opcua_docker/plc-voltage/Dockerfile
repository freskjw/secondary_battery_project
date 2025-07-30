# 도커파일
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY shared/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/lot_db_helper.py ./lot_db_helper.py
COPY plc-voltage/voltage_writer.py .

CMD ["python", "-u","voltage_writer.py"]