"""Aplicacion Celery compartida.

Cada worker importa este modulo y sobrescribe `include` con sus propias
tareas. La configuracion de colas, prioridades y reintentos es comun.
"""

from celery import Celery
from celery.signals import setup_logging

from services.shared.config import settings
from services.shared.logging_setup import setup_logging as _setup_logging
from services.shared.messaging.queues import (
    CELERY_TASK_QUEUES,
    CELERY_TASK_ROUTES,
    QUEUE_TEXT,
)

celery_app = Celery(
    "mediaintel",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_default_queue=QUEUE_TEXT,
    task_queues=CELERY_TASK_QUEUES,
    task_routes=CELERY_TASK_ROUTES,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=settings.task_hard_time_limit,
    task_soft_time_limit=settings.task_soft_time_limit,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    broker_transport_options={
        "priority_steps": [1, 3, 6, 10],
        "queue_order_strategy": "priority",
    },
    result_extended=True,
    result_expires=3600 * 24,
    timezone="UTC",
    enable_utc=True,
)


@setup_logging.connect
def _on_celery_setup_logging(**_kwargs):
    _setup_logging(level=settings.log_level)
