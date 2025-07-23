#도커파일
FROM python:3.11-slim
WORKDIR /app

COPY shared/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY vision2/vision2_writer.py .

CMD ["python", "vision2_writer.py"]