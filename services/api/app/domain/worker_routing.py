"""Reglas puras: que mime-type / extension va a que worker."""

from services.shared.messaging.queues import (
    QUEUE_AUDIO,
    QUEUE_IMAGE,
    QUEUE_TEXT,
)
from services.shared.models.enums import DataSourceType, WorkerType

_AUDIO_MIMES = {
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
    "audio/m4a",
}
_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}
_TEXT_MIMES = {"text/plain", "text/csv", "application/json"}


def classify_source(mime_type: str | None, filename: str | None) -> DataSourceType:
    mime = (mime_type or "").lower()
    name = (filename or "").lower()

    if mime in _AUDIO_MIMES or name.endswith(
        (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".webm")
    ):
        return DataSourceType.AUDIO
    if mime in _IMAGE_MIMES or name.endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff")
    ):
        return DataSourceType.IMAGE
    if mime in _TEXT_MIMES or name.endswith((".txt", ".csv", ".json", ".log")):
        return DataSourceType.TEXT
    if mime.startswith("video/"):
        return DataSourceType.VIDEO
    return DataSourceType.DOC


_TYPE_TO_WORKER: dict[DataSourceType, tuple[WorkerType, str, str]] = {
    DataSourceType.TEXT: (
        WorkerType.TEXT,
        QUEUE_TEXT,
        "worker_text.analyze_text",
    ),
    DataSourceType.AUDIO: (
        WorkerType.AUDIO,
        QUEUE_AUDIO,
        "worker_audio.transcribe_and_analyze",
    ),
    DataSourceType.IMAGE: (
        WorkerType.IMAGE,
        QUEUE_IMAGE,
        "worker_image.detect_objects",
    ),
    DataSourceType.VIDEO: (
        WorkerType.IMAGE,
        QUEUE_IMAGE,
        "worker_image.detect_objects",
    ),
    DataSourceType.DOC: (
        WorkerType.TEXT,
        QUEUE_TEXT,
        "worker_text.analyze_text",
    ),
}


def routing_for(source_type: DataSourceType) -> tuple[WorkerType, str, str]:
    return _TYPE_TO_WORKER[source_type]
