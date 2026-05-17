"""Wrapper sobre faster-whisper. Carga lazy del modelo.

faster-whisper consume CPU agresivamente; el worker se configura con
concurrency=1 a proposito para evitar saturar la maquina.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING

from services.shared.config import settings

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

_model: "WhisperModel | None" = None
_model_lock = Lock()


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    text: str
    language: str
    duration: float
    segments: list[TranscriptSegment]


def _get_model() -> "WhisperModel":
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel  # import diferido

            _model = WhisperModel(
                settings.whisper_model_size,
                device="cpu",
                compute_type="int8",
            )
    return _model


def transcribe(file_path: str) -> TranscriptResult:
    model = _get_model()
    segments_iter, info = model.transcribe(
        file_path,
        beam_size=1,
        vad_filter=True,
    )
    segments = [
        TranscriptSegment(start=s.start, end=s.end, text=s.text.strip())
        for s in segments_iter
    ]
    text = " ".join(s.text for s in segments).strip()
    return TranscriptResult(
        text=text,
        language=info.language,
        duration=info.duration,
        segments=segments,
    )
