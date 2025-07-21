

FROM python:3.11-slim

WORKDIR /app

COPY shared/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY opcua-bridge/opcua_to_db.py .
COPY shared/lot_db_helper.py .

CMD ["python", "opcua_to_db.py"]