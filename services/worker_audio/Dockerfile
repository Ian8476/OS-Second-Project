# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY services/shared/requirements.txt /app/services/shared/requirements.txt
COPY services/worker_audio/requirements.txt /app/services/worker_audio/requirements.txt
RUN pip install -r /app/services/worker_audio/requirements.txt

COPY services/shared /app/services/shared
COPY services/worker_audio /app/services/worker_audio

ENV PYTHONPATH=/app

CMD ["sh", "-c", "celery -A services.worker_audio.celery_app worker --loglevel=info --queues=${WORKER_QUEUE:-queue.audio} --concurrency=${WORKER_CONCURRENCY:-1} -n worker.audio@%h"]
