"""Tests puros (sin BD) del enrutador de workers."""

from services.api.app.domain.worker_routing import classify_source, routing_for
from services.shared.models.enums import DataSourceType, WorkerType


def test_text_mime_routes_to_text_worker():
    assert classify_source("text/plain", "notes.txt") == DataSourceType.TEXT
    worker, queue, task = routing_for(DataSourceType.TEXT)
    assert worker == WorkerType.TEXT
    assert queue == "queue.text"
    assert task == "worker_text.analyze_text"


def test_audio_extension_overrides_missing_mime():
    assert classify_source(None, "voice.mp3") == DataSourceType.AUDIO


def test_image_jpg_routes_to_image_worker():
    assert classify_source("image/jpeg", "evidence.jpg") == DataSourceType.IMAGE
    worker, queue, _ = routing_for(DataSourceType.IMAGE)
    assert worker == WorkerType.IMAGE
    assert queue == "queue.image"


def test_unknown_falls_back_to_doc_and_text_worker():
    assert classify_source("application/x-thingy", "x.thingy") == DataSourceType.DOC
    worker, queue, _ = routing_for(DataSourceType.DOC)
    assert worker == WorkerType.TEXT
    assert queue == "queue.text"
