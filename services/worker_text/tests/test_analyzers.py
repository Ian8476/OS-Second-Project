"""Tests puros de analizadores. No requieren broker ni BD."""

from services.worker_text.analyzers.keyword import find_keywords
from services.worker_text.analyzers.offensive import detect_offensive
from services.worker_text.analyzers.sentiment import analyze_sentiment


def test_keyword_matches_violence():
    findings = find_keywords("Voy a golpear a esa persona y matar al perro.")
    cats = {f.category for f in findings}
    assert "violence" in cats


def test_sentiment_strongly_negative_emits_finding():
    findings = analyze_sentiment("I hate everything, this is horrible, terrible, awful.")
    assert findings
    assert findings[0].category == "sentiment_negative"


def test_offensive_detects_tokens():
    findings = detect_offensive("this is total shit and fuck everything")
    assert findings
    assert findings[0].category == "offensive"


def test_no_findings_for_neutral_text():
    text = "Hoy fue un dia normal en la oficina, comimos pizza."
    assert find_keywords(text) == []
