"""Detector simple de lenguaje ofensivo: porcentaje de palabras tabu."""

from services.shared.models.enums import FindingCategory
from services.shared.workers_base import WorkerFinding

_OFFENSIVE = {
    "fuck", "shit", "bitch", "asshole", "bastard",
    "mierda", "puta", "pendejo", "cabron",
}


def detect_offensive(text: str) -> list[WorkerFinding]:
    tokens = [t.lower().strip(".,!?;:") for t in text.split()]
    if not tokens:
        return []
    hits = [t for t in tokens if t in _OFFENSIVE]
    if not hits:
        return []
    ratio = len(hits) / len(tokens)
    severity = 2 if ratio < 0.05 else 3 if ratio < 0.15 else 4
    return [
        WorkerFinding(
            category=FindingCategory.OFFENSIVE.value,
            severity=severity,
            confidence=min(1.0, 0.5 + ratio),
            evidence={
                "offensive_tokens": hits[:20],
                "ratio": round(ratio, 4),
                "total_tokens": len(tokens),
            },
        )
    ]
