"""Analisis por listas de keywords clasificadas por categoria/severidad.

Es deliberadamente simple: una lista por categoria + match exacto en
unicode lower. Para academia es suficiente y explicable en defensa.
"""

from __future__ import annotations

from services.shared.models.enums import FindingCategory
from services.shared.workers_base import WorkerFinding

KEYWORD_RULES: dict[FindingCategory, tuple[tuple[str, ...], int]] = {
    FindingCategory.VIOLENCE: (
        (
            "matar", "golpear", "asesinar", "violencia", "agredir",
            "kill", "hit", "punch", "beat",
        ),
        4,
    ),
    FindingCategory.THREATS: (
        ("te voy a", "vas a ver", "amenaza", "threat", "i will kill you"),
        5,
    ),
    FindingCategory.OFFENSIVE: (
        ("estupido", "idiota", "tarado", "moron", "stupid", "idiot"),
        2,
    ),
    FindingCategory.HATE_SPEECH: (
        ("odio a los", "deberian morir", "i hate"),
        4,
    ),
    FindingCategory.SELF_HARM: (
        ("suicidarme", "matarme", "kill myself", "self harm"),
        5,
    ),
}


def find_keywords(text: str) -> list[WorkerFinding]:
    norm = text.lower()
    findings: list[WorkerFinding] = []
    for category, (words, severity) in KEYWORD_RULES.items():
        matches = [w for w in words if w in norm]
        if not matches:
            continue
        snippet = _snippet_around(text, matches[0])
        findings.append(
            WorkerFinding(
                category=category.value,
                severity=severity,
                confidence=min(1.0, 0.6 + 0.1 * len(matches)),
                evidence={
                    "matched_keywords": matches,
                    "snippet": snippet,
                },
            )
        )
    return findings


def _snippet_around(text: str, keyword: str, span: int = 60) -> str:
    idx = text.lower().find(keyword.lower())
    if idx < 0:
        return text[:120]
    start = max(0, idx - span)
    end = min(len(text), idx + len(keyword) + span)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"
