FROM python:3.11-slim
WORKDIR /app
COPY shared/lot_db_helper.py ./lot_db_helper.py
COPY pack-batcher/pack_batcher.py ./
RUN pip install python-dotenv mysql-connector-python
CMD ["python","-u","pack_batcher.py"]