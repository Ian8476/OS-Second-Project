"""Tarea Celery del worker_audio: transcripcion + reanalisis."""

from __future__ import annotations

import os

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from services.shared.config import settings
from services.shared.logging_setup import get_logger
from services.shared.models.enums import FindingCategory
from services.shared.storage.minio_client import get_storage
from services.shared.workers_base import WorkerContext, WorkerFinding, run_subtask
from services.worker_audio.transcriber import transcribe
from services.worker_text.analyzers.keyword import find_keywords
from services.worker_text.analyzers.offensive import detect_offensive
from services.worker_text.analyzers.sentiment import analyze_sentiment

logger = get_logger("worker_audio")


def _transcript_findings(transcript_text: str, segments) -> list[WorkerFinding]:
    findings: list[WorkerFinding] = []
    findings.extend(find_keywords(transcript_text))
    findings.extend(analyze_sentiment(transcript_text))
    findings.extend(detect_offensive(transcript_text))
    findings.append(
        WorkerFinding(
            category=FindingCategory.KEYWORD_MATCH.value,
            severity=1,
            confidence=1.0,
            evidence={
                "transcript_preview": transcript_text[:500],
                "segments_count": len(segments),
            },
        )
    )
    return findings


@shared_task(
    name="worker_audio.transcribe_and_analyze",
    bind=True,
    max_retries=None,
    acks_late=True,
)
def transcribe_and_analyze(
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
            result = transcribe(tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        logger.info(
            "audio_transcribed",
            subtask_id=ctx.subtask_id,
            language=result.language,
            duration=result.duration,
            chars=len(result.text),
        )
        return _transcript_findings(result.text, result.segments)

    try:
        return run_subtask(
            task_id=self.request.id,
            subtask_id=subtask_id,
            case_id=case_id,
            storage_key=storage_key,
            worker_type="audio",
            extra=extra,
            do_work=do_work,
        )
    except Exception as exc:
        retries = self.request.retries or 0
        if retries >= settings.task_max_retries:
            logger.error(
                "audio_task_exhausted_retries",
                subtask_id=subtask_id,
                error=str(exc),
            )
            raise MaxRetriesExceededError(str(exc)) from exc
        countdown = settings.task_retry_backoff_base * (2**retries)
        raise self.retry(
            exc=exc, countdown=countdown, max_retries=settings.task_max_retries
        )
