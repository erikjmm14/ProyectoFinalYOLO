"""Tests del MissionPlanner usando dobles de prueba ligeros."""
from unittest.mock import MagicMock

import numpy as np
import pytest

from mission import MissionPlanner
from vision.detector import Detection


class FakeController:
    """Devuelve un frame distinto por cada movimiento lateral/forward."""
    def __init__(self, total_frames_per_table: int = 5):
        self.table_idx = 0
        self.frames_remaining = 0
        self.total_per_table = total_frames_per_table
        self.in_air = False
        self.battery = 100
        self.calls = []

    def connect(self): self.calls.append("connect"); return True
    def takeoff(self): self.calls.append("takeoff"); self.in_air = True
    def land(self): self.calls.append("land"); self.in_air = False
    def emergency(self): self.calls.append("emergency"); self.in_air = False
    def end(self): self.calls.append("end")
    def get_battery(self): return self.battery

    def _advance(self, prefix: str, cm: int):
        self.calls.append(f"{prefix}:{cm}")
        self.table_idx += 1
        self.frames_remaining = self.total_per_table

    def move_forward(self, cm): self._advance("forward", cm)
    def move_right(self, cm):   self._advance("right", cm)
    def move_left(self, cm):    self._advance("left", cm)

    def move_up(self, cm):
        self.calls.append(f"up:{cm}")
    def get_frame(self):
        if self.frames_remaining <= 0:
            return np.zeros((10, 10, 3), dtype=np.uint8)
        self.frames_remaining -= 1
        # un frame que codifica la mesa actual
        f = np.zeros((10, 10, 3), dtype=np.uint8)
        f[0, 0, 0] = self.table_idx
        return f


class FakeDetector:
    """Devuelve target en la mesa configurada."""
    def __init__(self, target_table: int, target_label: str = "book"):
        self.target = target_label
        self.target_table = target_table

    def detect(self, frame) -> list[Detection]:
        table = int(frame[0, 0, 0])
        if table == self.target_table:
            return [Detection(self.target, 0.9, (0, 0, 5, 5))]
        return []

    def target_found(self, detections):
        c = [d for d in detections if d.label == self.target]
        return max(c, key=lambda d: d.conf, default=None)


def test_mission_finds_target_at_table_3():
    ctrl = FakeController(total_frames_per_table=5)
    det = FakeDetector(target_table=3)
    mission = MissionPlanner(
        controller=ctrl, detector=det, num_tables=6,
        scan_max_frames=5, confirm_k_frames=3, hold_time_sec=0,
        scan_time_sec=0, show=False,
    )
    mission.run()
    # Avanzó 3 veces (lateral default = right) y aterrizó
    move_calls = [c for c in ctrl.calls if c.startswith("right:")]
    assert len(move_calls) == 3
    assert "land" in ctrl.calls


def test_mission_completes_all_tables_when_target_absent():
    ctrl = FakeController(total_frames_per_table=5)
    det = FakeDetector(target_table=99)  # nunca aparece
    mission = MissionPlanner(
        controller=ctrl, detector=det, num_tables=6,
        scan_max_frames=5, confirm_k_frames=3, hold_time_sec=0,
        scan_time_sec=0, show=False,
    )
    mission.run()
    move_calls = [c for c in ctrl.calls if c.startswith("right:")]
    assert len(move_calls) == 6
    assert "land" in ctrl.calls


def test_mission_uses_forward_direction_when_requested():
    ctrl = FakeController(total_frames_per_table=5)
    det = FakeDetector(target_table=99)
    mission = MissionPlanner(
        controller=ctrl, detector=det, num_tables=2,
        scan_max_frames=5, confirm_k_frames=3, hold_time_sec=0,
        scan_time_sec=0, show=False, direction="forward",
    )
    mission.run()
    assert sum(1 for c in ctrl.calls if c.startswith("forward:")) == 2


def test_mission_rejects_invalid_direction():
    ctrl = FakeController()
    det = FakeDetector(target_table=99)
    with pytest.raises(ValueError, match="direction"):
        MissionPlanner(controller=ctrl, detector=det, num_tables=1,
                       direction="up", show=False)


def test_mission_aborts_on_low_battery_preflight():
    ctrl = FakeController()
    ctrl.battery = 10  # debajo del mínimo
    det = FakeDetector(target_table=99)
    mission = MissionPlanner(
        controller=ctrl, detector=det, num_tables=6,
        scan_max_frames=5, confirm_k_frames=3, hold_time_sec=0,
        scan_time_sec=0, show=False,
    )
    with pytest.raises(RuntimeError, match=r"(?i)bater"):
        mission.run()
    assert "takeoff" not in ctrl.calls


def test_mission_always_lands_even_on_exception():
    ctrl = FakeController()
    det = MagicMock()
    det.detect.side_effect = RuntimeError("boom")
    mission = MissionPlanner(
        controller=ctrl, detector=det, num_tables=6,
        scan_max_frames=5, confirm_k_frames=3, hold_time_sec=0,
        scan_time_sec=0, show=False,
    )
    with pytest.raises(RuntimeError):
        mission.run()
    assert "land" in ctrl.calls
