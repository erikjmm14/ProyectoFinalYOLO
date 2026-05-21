"""Wrapper de djitellopy con la misma interfaz que MockController."""

import logging
import time

from djitellopy import Tello

log = logging.getLogger(__name__)


class TelloController:
    def __init__(self, video_source=None):
        # video_source se ignora; está en la firma para paridad con MockController.
        self._video_source = video_source
        self.tello = Tello()
        self.in_air = False

    def connect(self) -> bool:
        log.info("[TELLO] connect")
        self.tello.connect()
        self.tello.streamon()
        time.sleep(2)  # dejar que el stream inicie
        return True

    def takeoff(self) -> None:
        log.info("[TELLO] takeoff")
        self.tello.takeoff()
        self.in_air = True

    def land(self) -> None:
        log.info("[TELLO] land")
        if self.in_air:
            self.tello.land()
            self.in_air = False

    def move_forward(self, cm: int) -> None:
        log.info(f"[TELLO] move_forward {cm}cm")
        # djitellopy clamp: el Tello acepta 20–500 cm por comando
        cm = max(20, min(500, int(cm)))
        self.tello.move_forward(cm)

    def get_frame(self):
        return self.tello.get_frame_read().frame

    def get_battery(self) -> int:
        return int(self.tello.get_battery())

    def emergency(self) -> None:
        log.warning("[TELLO] emergency")
        try:
            self.tello.emergency()
        finally:
            self.in_air = False

    def end(self) -> None:
        log.info("[TELLO] end")
        try:
            self.tello.streamoff()
        finally:
            self.tello.end()
