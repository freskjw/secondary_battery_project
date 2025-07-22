# cp-calculator/Dockerfile

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 1) shared/requirements.txt 를 복사
COPY shared/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 2) 스크립트·환경파일 복사
COPY cp-calculator/cp_calculator.py ./cp_calculator.py
COPY config.env ./config.env

CMD ["python","-u","cp_calculator.py"]