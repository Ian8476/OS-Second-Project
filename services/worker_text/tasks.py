"""Tareas Celery del worker_text. Una sola publica: `analyze_text`."""

from __future__ import annotations

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from services.shared.config import settings
from services.shared.logging_setup import get_logger
from services.shared.storage.minio_client import get_storage
from services.shared.workers_base import WorkerContext, WorkerFinding, run_subtask
from services.worker_text.analyzers.keyword import find_keywords
from services.worker_text.analyzers.offensive import detect_offensive
from services.worker_text.analyzers.sentiment import analyze_sentiment

logger = get_logger("worker_text")


def _analyze(text: str) -> list[WorkerFinding]:
    findings: list[WorkerFinding] = []
    findings.extend(find_keywords(text))
    findings.extend(analyze_sentiment(text))
    findings.extend(detect_offensive(text))
    return findings


@shared_task(
    name="worker_text.analyze_text",
    bind=True,
    max_retries=None,
    acks_late=True,
)
def analyze_text(
    self,
    *,
    subtask_id: str,
    case_id: str,
    storage_key: str | None,
    extra: dict | None = None,
):
    """Descarga el texto desde MinIO y aplica los analizadores."""
    extra = extra or {}

    def do_work(ctx: WorkerContext) -> list[WorkerFinding]:
        if not ctx.storage_key:
            return []
        raw = get_storage().get_bytes(ctx.storage_key)
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        return _analyze(text)

    try:
        return run_subtask(
            task_id=self.request.id,
            subtask_id=subtask_id,
            case_id=case_id,
            storage_key=storage_key,
            worker_type="text",
            extra=extra,
            do_work=do_work,
        )
    except Exception as exc:
        retries = self.request.retries or 0
        if retries >= settings.task_max_retries:
            logger.error(
                "text_task_exhausted_retries",
                subtask_id=subtask_id,
                error=str(exc),
            )
            raise MaxRetriesExceededError(str(exc)) from exc
        countdown = settings.task_retry_backoff_base * (2**retries)
        logger.warning(
            "text_task_retry",
            subtask_id=subtask_id,
            attempt=retries + 1,
            countdown=countdown,
            error=str(exc),
        )
        raise self.retry(
            exc=exc, countdown=countdown, max_retries=settings.task_max_retries
        )
