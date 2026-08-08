FROM python:3.12-slim
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agents agents
COPY workflow workflow
COPY tools tools
COPY runbooks runbooks
CMD ["uvicorn", "agents.api:app", "--host", "0.0.0.0", "--port", "8081"]
