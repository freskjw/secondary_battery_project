FROM python:3.11-slim
WORKDIR /app
COPY opcua-server/opcua_server.py ./
RUN pip install asyncua python-dotenv
CMD ["python","-u","opcua_server.py"]