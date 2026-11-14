FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scoring.py scaling.py proxy.py k8s_client.py main.py ./
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "--factory", "main:app_from_env", "--host", "0.0.0.0", "--port", "8000"]
