FROM python:3.11-slim
WORKDIR /app
COPY shared/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY simulator/sim_line.py .
CMD ["python", "sim_line.py"]
