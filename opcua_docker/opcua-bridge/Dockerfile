FROM python:3.11-slim
WORKDIR /app
COPY shared/lot_db_helper.py ./lot_db_helper.py
COPY opcua-bridge/opcua_to_db.py ./
RUN pip install asyncua python-dotenv mysql-connector-python
CMD ["python","-u","opcua_to_db.py"]