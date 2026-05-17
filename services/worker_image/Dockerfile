# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY services/shared/requirements.txt /app/services/shared/requirements.txt
COPY services/worker_image/requirements.txt /app/services/worker_image/requirements.txt
RUN pip install -r /app/services/worker_image/requirements.txt

COPY services/shared /app/services/shared
COPY services/worker_image /app/services/worker_image

ENV PYTHONPATH=/app

CMD ["sh", "-c", "celery -A services.worker_image.celery_app worker --loglevel=info --queues=${WORKER_QUEUE:-queue.image} --concurrency=${WORKER_CONCURRENCY:-2} -n worker.image@%h"]
