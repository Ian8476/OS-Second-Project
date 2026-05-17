"""Reglas que convierten detecciones YOLO en findings categorizados."""

from __future__ import annotations

from services.shared.models.enums import FindingCategory
from services.shared.workers_base import WorkerFinding
from services.worker_image.detectors.yolo_objects import Detection

_WEAPONS = {
    "knife", "scissors", "gun", "rifle", "pistol", "fire arm", "weapon",
}
_PERSON_LABELS = {"person"}
_DANGEROUS_OBJECTS = {"baseball bat", "bottle"}


def classify(detections: list[Detection]) -> list[WorkerFinding]:
    findings: list[WorkerFinding] = []

    weapon_hits = [d for d in detections if d.label.lower() in _WEAPONS]
    if weapon_hits:
        top = max(weapon_hits, key=lambda d: d.confidence)
        findings.append(
            WorkerFinding(
                category=FindingCategory.WEAPON_DETECTED.value,
                severity=5,
                confidence=top.confidence,
                evidence={
                    "label": top.label,
                    "bbox": list(top.bbox),
                    "all_weapons": [
                        {"label": d.label, "confidence": d.confidence}
                        for d in weapon_hits
                    ],
                },
            )
        )

    person_hits = [d for d in detections if d.label.lower() in _PERSON_LABELS]
    if person_hits:
        top = max(person_hits, key=lambda d: d.confidence)
        findings.append(
            WorkerFinding(
                category=FindingCategory.PERSON_DETECTED.value,
                severity=1,
                confidence=top.confidence,
                evidence={
                    "count": len(person_hits),
                    "max_confidence": top.confidence,
                },
            )
        )

    dangerous_hits = [d for d in detections if d.label.lower() in _DANGEROUS_OBJECTS]
    if dangerous_hits:
        top = max(dangerous_hits, key=lambda d: d.confidence)
        findings.append(
            WorkerFinding(
                category=FindingCategory.OBJECT_DETECTED.value,
                severity=2,
                confidence=top.confidence,
                evidence={
                    "label": top.label,
                    "all": [
                        {"label": d.label, "confidence": d.confidence}
                        for d in dangerous_hits
                    ],
                },
            )
        )

    if detections and not findings:
        labels = sorted({d.label for d in detections})[:10]
        findings.append(
            WorkerFinding(
                category=FindingCategory.OBJECT_DETECTED.value,
                severity=1,
                confidence=max(d.confidence for d in detections),
                evidence={"labels": labels, "total_detections": len(detections)},
            )
        )

    return findings
