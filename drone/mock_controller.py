"""Controller falso para desarrollo y pruebas sin dron real.

Acepta cualquier objeto con métodos `.read()` y `.release()` (duck typing),
incluyendo un `cv2.VideoCapture` con webcam (`0`) o archivo de video/imagen.
"""

import logging
import time
from typing import Union

import cv2

log = logging.getLogger(__name__)


class MockController:
    def __init__(self, video_source: Union[int, str, object] = 0):
        if isinstance(video_source, (int, str)):
            self.cap = cv2.VideoCapture(video_source)
            if not self.cap.isOpened():
                raise RuntimeError(f"No pude abrir video_source={video_source!r}")
        else:
            self.cap = video_source  # objeto pre-construido (para tests)
        self.in_air = False
        self._battery = 100

    def connect(self) -> bool:
        log.info("[MOCK] connect")
        return True

    def takeoff(self) -> None:
        log.info("[MOCK] takeoff")
        self.in_air = True
        time.sleep(1)

    def land(self) -> None:
        log.info("[MOCK] land")
        self.in_air = False
        time.sleep(1)

    def move_forward(self, cm: int) -> None:
        log.info(f"[MOCK] move_forward {cm}cm")
        time.sleep(cm / 50)

    def get_frame(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def get_battery(self) -> int:
        return self._battery

    def emergency(self) -> None:
        log.warning("[MOCK] emergency")
        self.in_air = False

    def end(self) -> None:
        log.info("[MOCK] end")
        self.cap.release()
