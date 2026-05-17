# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/shared/requirements.txt /app/services/shared/requirements.txt
COPY services/api/requirements.txt /app/services/api/requirements.txt
RUN pip install -r /app/services/api/requirements.txt

COPY services/shared /app/services/shared
COPY services/api /app/services/api

ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["sh", "-c", "alembic -c /app/services/shared/alembic.ini upgrade head && uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000"]
