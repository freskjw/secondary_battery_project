FROM python:3.11-slim

WORKDIR /app

COPY shared/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY plc-voltage/voltage_writer.py .

CMD ["python", "voltage_writer.py"]