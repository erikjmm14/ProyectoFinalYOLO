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
        time.sleep(3)  # estabilización tras takeoff antes de aceptar más comandos
        self._reassert_sdk_mode()

    def _post_command_settle(self) -> None:
        time.sleep(1)

    def _reassert_sdk_mode(self) -> None:
        """Reenvía el comando 'command' para asegurar que el Tello sigue en modo SDK.

        Algunos Tello revierten a modo App tras takeoff, causando 'error Not joystick'
        en los siguientes movimientos. Este re-arme suele solucionarlo.
        """
        try:
            self.tello.send_control_command("command", timeout=3)
            log.info("[TELLO] modo SDK re-armado")
        except Exception as e:
            log.warning(f"[TELLO] re-arme SDK falló: {e}")

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
        self._post_command_settle()

    def move_up(self, cm: int) -> None:
        log.info(f"[TELLO] move_up {cm}cm")
        cm = max(20, min(500, int(cm)))
        self.tello.move_up(cm)
        self._post_command_settle()

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
