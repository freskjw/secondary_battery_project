FROM python:3.11-slim
WORKDIR /app
COPY shared/lot_db_helper.py ./lot_db_helper.py
COPY plc-voltage/voltage_writer.py ./
# ⬇⬇⬇ mysql-connector-python 추가
RUN pip install --no-cache-dir asyncua python-dotenv pymcprotocol mysql-connector-python
CMD ["python","-u","voltage_writer.py"]