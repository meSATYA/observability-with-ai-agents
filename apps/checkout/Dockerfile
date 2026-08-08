FROM python:3.12-slim
WORKDIR /app
COPY apps/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/service.py .
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]
