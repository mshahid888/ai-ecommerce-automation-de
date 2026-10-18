# Backend for the AI E-Commerce Automation demo (German).
# Build: docker build -t ecommerce-demo-backend .
# Run:   docker run -d --name ecommerce-demo-backend --env-file .env.production -p 127.0.0.1:8001:8000 ecommerce-demo-backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p ./data

# SQLite demo DB lives here; mount a volume in production to persist it.
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
