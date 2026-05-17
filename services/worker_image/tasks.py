"""Tarea Celery del worker_image: YOLO + clasificacion en findings."""

from __future__ import annotations

import os

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from services.shared.config import settings
from services.shared.logging_setup import get_logger
from services.shared.storage.minio_client import get_storage
from services.shared.workers_base import WorkerContext, WorkerFinding, run_subtask
from services.worker_image.detectors.content_filter import classify
from services.worker_image.detectors.yolo_objects import detect

logger = get_logger("worker_image")


@shared_task(
    name="worker_image.detect_objects",
    bind=True,
    max_retries=None,
    acks_late=True,
)
def detect_objects(
    self,
    *,
    subtask_id: str,
    case_id: str,
    storage_key: str | None,
    extra: dict | None = None,
):
    extra = extra or {}

    def do_work(ctx: WorkerContext) -> list[WorkerFinding]:
        if not ctx.storage_key:
            return []
        suffix = os.path.splitext(ctx.storage_key)[1] or ".bin"
        tmp_path = get_storage().download_to_tempfile(ctx.storage_key, suffix=suffix)
        try:
            detections = detect(tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        logger.info(
            "image_detected",
            subtask_id=ctx.subtask_id,
            detections=len(detections),
        )
        return classify(detections)

    try:
        return run_subtask(
            task_id=self.request.id,
            subtask_id=subtask_id,
            case_id=case_id,
            storage_key=storage_key,
            worker_type="image",
            extra=extra,
            do_work=do_work,
        )
    except Exception as exc:
        retries = self.request.retries or 0
        if retries >= settings.task_max_retries:
            logger.error(
                "image_task_exhausted_retries",
                subtask_id=subtask_id,
                error=str(exc),
            )
            raise MaxRetriesExceededError(str(exc)) from exc
        countdown = settings.task_retry_backoff_base * (2**retries)
        raise self.retry(
            exc=exc, countdown=countdown, max_retries=settings.task_max_retries
        )
