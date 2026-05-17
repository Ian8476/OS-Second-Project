"""Tests del classifier de detecciones, sin invocar YOLO."""

from services.worker_image.detectors.content_filter import classify
from services.worker_image.detectors.yolo_objects import Detection


def test_weapon_detection_emits_high_severity():
    detections = [Detection(label="knife", confidence=0.91, bbox=(0, 0, 10, 10))]
    findings = classify(detections)
    cats = {f.category for f in findings}
    assert "weapon_detected" in cats
    weapon = next(f for f in findings if f.category == "weapon_detected")
    assert weapon.severity == 5


def test_only_person_emits_low_severity():
    detections = [Detection(label="person", confidence=0.88, bbox=(0, 0, 10, 10))]
    findings = classify(detections)
    cats = {f.category for f in findings}
    assert "person_detected" in cats
    person = next(f for f in findings if f.category == "person_detected")
    assert person.severity == 1


def test_empty_detections_no_findings():
    assert classify([]) == []
