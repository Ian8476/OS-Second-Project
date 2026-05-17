"""Cliente Celery compartido y constantes de colas."""

from services.shared.messaging.celery_app import celery_app
from services.shared.messaging.queues import QUEUE_AGGREGATE, QUEUE_AUDIO, QUEUE_IMAGE, QUEUE_TEXT

__all__ = [
    "celery_app",
    "QUEUE_TEXT",
    "QUEUE_AUDIO",
    "QUEUE_IMAGE",
    "QUEUE_AGGREGATE",
]
