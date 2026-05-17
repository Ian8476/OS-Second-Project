"""Analisis de sentimiento con VADER.

VADER funciona bien para textos cortos en ingles; para espanol los
resultados son aceptables pero no perfectos. Sirve como evidencia
adicional, no como unica senal.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from services.shared.models.enums import FindingCategory
from services.shared.workers_base import WorkerFinding

_analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str) -> list[WorkerFinding]:
    if not text.strip():
        return []
    scores = _analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound > -0.5:
        return []
    severity = 3 if compound > -0.75 else 4
    return [
        WorkerFinding(
            category=FindingCategory.SENTIMENT_NEGATIVE.value,
            severity=severity,
            confidence=min(1.0, abs(compound)),
            evidence={"scores": scores, "snippet": text[:200]},
        )
    ]
