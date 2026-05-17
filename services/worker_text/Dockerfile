# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/shared/requirements.txt /app/services/shared/requirements.txt
COPY services/worker_text/requirements.txt /app/services/worker_text/requirements.txt
RUN pip install -r /app/services/worker_text/requirements.txt

COPY services/shared /app/services/shared
COPY services/worker_text /app/services/worker_text

ENV PYTHONPATH=/app

CMD ["sh", "-c", "celery -A services.worker_text.celery_app worker --loglevel=info --queues=${WORKER_QUEUE:-queue.text} --concurrency=${WORKER_CONCURRENCY:-4} -n worker.text@%h"]
