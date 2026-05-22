"""YOLOv8 wrapper para detección de objetos COCO."""

from dataclasses import dataclass
from ultralytics import YOLO


@dataclass(frozen=True)
class Detection:
    label: str
    conf: float
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)


class YOLODetector:
    def __init__(self, model_path: str, target: str | None, conf_threshold: float):
        """target=None deshabilita la validación y target_found() siempre devuelve None.
        En ese modo, detect() sigue devolviendo TODAS las clases COCO ≥ umbral.
        """
        self.model = YOLO(model_path)
        self.target = target
        self.conf_threshold = conf_threshold
        if target is not None:
            self._validate_target()

    def _validate_target(self) -> None:
        valid = set(self.model.names.values())
        if self.target not in valid:
            raise ValueError(
                f"Target '{self.target}' no es una clase COCO. "
                f"Algunas válidas: {sorted(valid)[:10]}..."
            )

    def detect(self, frame) -> list[Detection]:
        results = self.model(frame, verbose=False)[0]
        detections: list[Detection] = []
        for box in results.boxes:
            conf = float(box.conf)
            if conf < self.conf_threshold:
                continue
            label = self.model.names[int(box.cls)]
            xyxy = tuple(float(v) for v in box.xyxy[0].tolist())
            detections.append(Detection(label=label, conf=conf, bbox=xyxy))
        return detections

    def target_found(self, detections: list[Detection]) -> Detection | None:
        if self.target is None:
            return None
        candidates = [d for d in detections if d.label == self.target]
        return max(candidates, key=lambda d: d.conf, default=None)
