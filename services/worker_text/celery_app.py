"""Celery app del worker_text. Reusa el celery_app compartido."""

from services.shared.messaging.celery_app import celery_app
from services.worker_text import tasks  # noqa: F401 - registra tareas

__all__ = ["celery_app"]
