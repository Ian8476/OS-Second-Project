"""Tests del paso de findings sobre un transcript, sin invocar Whisper."""

from services.worker_audio.tasks import _transcript_findings


def test_transcript_includes_keyword_finding():
    findings = _transcript_findings("voy a golpear y matar", segments=[])
    categories = {f.category for f in findings}
    assert "violence" in categories


def test_neutral_transcript_only_has_summary_finding():
    findings = _transcript_findings("hola mundo todo tranquilo", segments=[])
    categories = [f.category for f in findings]
    assert "keyword_match" in categories
