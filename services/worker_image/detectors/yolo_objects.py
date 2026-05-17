"""Wrapper sobre YOLOv8 nano para deteccion de objetos."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING

from services.shared.config import settings

if TYPE_CHECKING:
    from ultralytics import YOLO

_model: "YOLO | None" = None
_model_lock = Lock()


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2


def _get_model() -> "YOLO":
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from ultralytics import YOLO  # type: ignore

            _model = YOLO(settings.yolo_model)
    return _model


def detect(image_path: str, conf_threshold: float = 0.35) -> list[Detection]:
    model = _get_model()
    results = model.predict(image_path, conf=conf_threshold, imgsz=640, verbose=False)
    detections: list[Detection] = []
    for r in results:
        if r.boxes is None:
            continue
        names = r.names
        for box, cls_id, score in zip(
            r.boxes.xyxy.cpu().numpy(),
            r.boxes.cls.cpu().numpy(),
            r.boxes.conf.cpu().numpy(),
        ):
            label = names.get(int(cls_id), str(int(cls_id)))
            x1, y1, x2, y2 = (float(x) for x in box.tolist())
            detections.append(
                Detection(
                    label=label,
                    confidence=float(score),
                    bbox=(x1, y1, x2, y2),
                )
            )
    return detections
