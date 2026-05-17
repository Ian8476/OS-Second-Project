"""Celery app del worker_audio."""

from services.shared.messaging.celery_app import celery_app
from services.worker_audio import tasks  # noqa: F401

__all__ = ["celery_app"]
