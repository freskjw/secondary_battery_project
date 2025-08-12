FROM python:3.11-slim
WORKDIR /app

# tzdata (ZoneInfo) - 비대화형
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Seoul

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY . /app

CMD ["python", "-u", "seed_dummy.py"]