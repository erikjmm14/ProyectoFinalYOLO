import pytest
import cv2
from pathlib import Path
from vision.detector import YOLODetector, Detection


FIXTURE = Path("tests/fixtures/bus.jpg")


@pytest.fixture(scope="module")
def detector_person():
    return YOLODetector(model_path="yolov8n.pt", target="person", conf_threshold=0.5)


@pytest.fixture(scope="module")
def bus_frame():
    if not FIXTURE.exists():
        pytest.skip(f"Falta {FIXTURE}; corre el step 1 de Task 3.")
    return cv2.imread(str(FIXTURE))


def test_detect_returns_list_of_detection(detector_person, bus_frame):
    detections = detector_person.detect(bus_frame)
    assert isinstance(detections, list)
    assert all(isinstance(d, Detection) for d in detections)


def test_detect_finds_person_in_bus_image(detector_person, bus_frame):
    detections = detector_person.detect(bus_frame)
    labels = {d.label for d in detections}
    assert "person" in labels


def test_target_found_returns_highest_conf(detector_person, bus_frame):
    detections = detector_person.detect(bus_frame)
    best = detector_person.target_found(detections)
    assert best is not None
    assert best.label == "person"


def test_target_found_returns_none_when_absent():
    det = YOLODetector(model_path="yolov8n.pt", target="zebra", conf_threshold=0.9)
    fake_detections = [Detection("person", 0.9, (0, 0, 100, 100))]
    assert det.target_found(fake_detections) is None


def test_invalid_target_raises():
    with pytest.raises(ValueError, match="no es una clase COCO"):
        YOLODetector(model_path="yolov8n.pt", target="termo", conf_threshold=0.5)
