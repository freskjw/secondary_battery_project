FROM python:3.11-slim
WORKDIR /app
COPY cp-calculator/cp_calculator.py ./
RUN pip install python-dotenv mysql-connector-python numpy
CMD ["python","-u","cp_calculator.py"]