"""Celery app del worker_image."""

from services.shared.messaging.celery_app import celery_app
from services.worker_image import tasks  # noqa: F401

__all__ = ["celery_app"]
