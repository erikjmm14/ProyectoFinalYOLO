import pytest
import numpy as np
from drone.mock_controller import MockController


class FakeCapture:
    """Capture que devuelve N frames y luego termina."""
    def __init__(self, n_frames: int = 3):
        self.n_frames = n_frames
        self._read_count = 0
        self.released = False

    def read(self):
        if self._read_count >= self.n_frames:
            return False, None
        self._read_count += 1
        return True, np.zeros((480, 640, 3), dtype=np.uint8)

    def release(self):
        self.released = True


def test_mock_lifecycle():
    ctrl = MockController(video_source=FakeCapture(n_frames=3))
    assert ctrl.connect() is True
    ctrl.takeoff()
    assert ctrl.in_air is True
    ctrl.move_forward(80)
    frame = ctrl.get_frame()
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    assert ctrl.get_battery() == 100
    ctrl.land()
    assert ctrl.in_air is False
    ctrl.end()


def test_mock_get_frame_returns_none_when_exhausted():
    cap = FakeCapture(n_frames=1)
    ctrl = MockController(video_source=cap)
    ctrl.get_frame()
    assert ctrl.get_frame() is None


def test_mock_emergency_sets_in_air_false():
    ctrl = MockController(video_source=FakeCapture(n_frames=1))
    ctrl.takeoff()
    ctrl.emergency()
    assert ctrl.in_air is False


def test_mock_end_releases_capture():
    cap = FakeCapture(n_frames=1)
    ctrl = MockController(video_source=cap)
    ctrl.end()
    assert cap.released is True
