"""Orquestador de la misión: takeoff -> scan por mesa -> hover -> land."""

import logging
import threading
import time

import cv2

import config

log = logging.getLogger(__name__)


class MissionPlanner:
    def __init__(self, controller, detector, num_tables: int,
                 scan_time_sec: float = config.SCAN_TIME_SEC,
                 scan_max_frames: int = config.SCAN_MAX_FRAMES,
                 confirm_k_frames: int = config.CONFIRM_K_FRAMES,
                 hold_time_sec: float = config.HOLD_TIME_SEC,
                 table_distance_cm: int = config.TABLE_DISTANCE_CM,
                 battery_preflight_min: int = config.BATTERY_PREFLIGHT_MIN,
                 battery_abort_min: int = config.BATTERY_ABORT_MIN,
                 flight_height_cm: int = config.FLIGHT_HEIGHT_CM,
                 show: bool = True):
        self.ctrl = controller
        self.det = detector
        self.num_tables = num_tables
        self.scan_time_sec = scan_time_sec
        self.scan_max_frames = scan_max_frames
        self.confirm_k_frames = confirm_k_frames
        self.hold_time_sec = hold_time_sec
        self.table_distance_cm = table_distance_cm
        self.battery_preflight_min = battery_preflight_min
        self.battery_abort_min = battery_abort_min
        self.flight_height_cm = flight_height_cm
        self.show = show

        # Estado compartido con el thread de preview en vivo
        self._latest_detections: list = []
        self._preview_stop = threading.Event()
        self._preview_thread: threading.Thread | None = None
        self._abort_requested = False

    def run(self) -> bool:
        """Ejecuta la misión. Devuelve True si encontró el objetivo."""
        found = False
        try:
            self._preflight()
            self._start_live_preview()
            self.ctrl.takeoff()
            self._ascend_to_flight_height()
            found = self._fly_mission()
        finally:
            self._stop_live_preview()
            try:
                self.ctrl.land()
            except Exception as e:
                log.warning(f"land() falló: {e}; llamando emergency()")
                try:
                    self.ctrl.emergency()
                except Exception:
                    pass
            self.ctrl.end()
            if self.show:
                cv2.destroyAllWindows()
        return found

    def _preflight(self) -> None:
        log.info("Preflight checks...")
        self.ctrl.connect()
        bat = self.ctrl.get_battery()
        log.info(f"Batería: {bat}%")
        if bat < self.battery_preflight_min:
            raise RuntimeError(
                f"Batería insuficiente: {bat}% < mínimo {self.battery_preflight_min}%"
            )

    def _ascend_to_flight_height(self) -> None:
        """Sube del altura de takeoff por defecto (~80 cm) a FLIGHT_HEIGHT_CM.

        Si falla el move_up (algunos Tello revierten a modo App), la misión
        continúa a la altura por defecto en vez de abortar.
        """
        delta = self.flight_height_cm - 80
        if delta < 20:
            return
        try:
            self.ctrl.move_up(delta)
        except Exception as e:
            log.warning(
                f"move_up({delta}) falló: {e}. Continuando a altura por defecto (~80cm). "
                f"Para forzar 80cm sin error pon FLIGHT_HEIGHT_CM=80 en config.py."
            )

    def _fly_mission(self) -> bool:
        for i in range(1, self.num_tables + 1):
            log.info(f"--- Mesa {i}/{self.num_tables} ---")
            self.ctrl.move_forward(self.table_distance_cm)

            if self._scan_for_target(table_idx=i):
                log.info(f"Objetivo '{self.det.target}' encontrado en mesa {i}")
                self._hold()
                return True

            if self._battery_too_low():
                log.warning("Batería baja; abortando misión")
                return False

        log.info("Recorrí todas las mesas sin encontrar el objetivo")
        return False

    def _scan_for_target(self, table_idx: int) -> bool:
        """Escanea la mesa actual; devuelve True si confirma el target."""
        positives = 0
        deadline = time.time() + self.scan_time_sec
        frames_seen = 0

        while frames_seen < self.scan_max_frames:
            if self._abort_requested:
                raise KeyboardInterrupt("Abort manual con 'q'")
            # Respeta el límite de tiempo sólo cuando scan_time_sec > 0
            if self.scan_time_sec > 0 and time.time() >= deadline:
                break

            frame = self.ctrl.get_frame()
            if frame is None:
                continue
            frames_seen += 1

            detections = self.det.detect(frame)
            self._latest_detections = detections  # publica para el preview
            hit = self.det.target_found(detections)
            if hit is not None:
                positives += 1
                log.info(f"  detección {positives}/{self.confirm_k_frames} "
                         f"(conf={hit.conf:.2f}) en mesa {table_idx}")

            if positives >= self.confirm_k_frames:
                return True

        return False

    def _hold(self) -> None:
        log.info(f"Hover {self.hold_time_sec}s sobre el objetivo")
        time.sleep(self.hold_time_sec)

    def _battery_too_low(self) -> bool:
        bat = self.ctrl.get_battery()
        return bat < self.battery_abort_min

    def _start_live_preview(self) -> None:
        """Arranca un thread que muestra el feed del dron durante toda la misión."""
        if not self.show:
            return
        self._preview_stop.clear()
        self._abort_requested = False
        self._preview_thread = threading.Thread(
            target=self._preview_loop, name="LivePreview", daemon=True,
        )
        self._preview_thread.start()
        log.info("Live preview iniciado (presiona 'q' en la ventana para abortar)")

    def _stop_live_preview(self) -> None:
        if not self.show or self._preview_thread is None:
            return
        self._preview_stop.set()
        self._preview_thread.join(timeout=2)
        self._preview_thread = None

    def _preview_loop(self) -> None:
        """Loop del thread: lee frames, los muestra con las últimas detecciones."""
        while not self._preview_stop.is_set():
            try:
                frame = self.ctrl.get_frame()
            except Exception as e:
                log.warning(f"Preview: error leyendo frame: {e}")
                time.sleep(0.1)
                continue
            if frame is None:
                time.sleep(0.05)
                continue
            self._render(frame, self._latest_detections)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self._abort_requested = True
                break

    def _render(self, frame, detections) -> None:
        for d in detections:
            x1, y1, x2, y2 = (int(v) for v in d.bbox)
            color = (0, 255, 0) if d.label == self.det.target else (255, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{d.label} {d.conf:.2f}", (x1, max(15, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        cv2.imshow("Tello YOLO", frame)
