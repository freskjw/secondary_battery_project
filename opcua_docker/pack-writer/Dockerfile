FROM python:3.11-slim
WORKDIR /app
COPY shared/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/lot_db_helper.py .
COPY pack-writer/pack_writer.py .
CMD ["python", "pack_writer.py"]