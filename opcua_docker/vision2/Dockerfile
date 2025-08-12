FROM python:3.11-slim
WORKDIR /app
COPY shared/lot_db_helper.py ./lot_db_helper.py
COPY vision2/vision2_writer.py ./
# ⬇⬇⬇ mysql-connector-python 추가
RUN pip install --no-cache-dir asyncua python-dotenv pymcprotocol mysql-connector-python
CMD ["python","-u","vision2_writer.py"]