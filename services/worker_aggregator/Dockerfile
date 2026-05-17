# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias de WeasyPrint para renderizar HTML -> PDF.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

COPY services/shared/requirements.txt /app/services/shared/requirements.txt
COPY services/worker_aggregator/requirements.txt /app/services/worker_aggregator/requirements.txt
RUN pip install -r /app/services/worker_aggregator/requirements.txt

COPY services/shared /app/services/shared
COPY services/worker_aggregator /app/services/worker_aggregator

ENV PYTHONPATH=/app

CMD ["sh", "-c", "celery -A services.worker_aggregator.celery_app worker --loglevel=info --queues=${WORKER_QUEUE:-queue.aggregate} --concurrency=${WORKER_CONCURRENCY:-2} -n worker.aggregator@%h"]
