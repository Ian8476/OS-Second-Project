"""Celery app del aggregator."""

from services.shared.messaging.celery_app import celery_app
from services.worker_aggregator import tasks  # noqa: F401

__all__ = ["celery_app"]
