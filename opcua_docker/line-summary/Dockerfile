FROM python:3.11-slim
WORKDIR /app
COPY line-summary/summary_scheduler.py ./
RUN pip install python-dotenv mysql-connector-python
CMD ["python","-u","summary_scheduler.py"]