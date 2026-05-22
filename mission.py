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
                 direction: str = "right",
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
        if direction not in ("right", "left", "forward"):
            raise ValueError(f"direction inválida: {direction!r}. Usa right|left|forward.")
        self.direction = direction
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
        move_fn = getattr(self.ctrl, f"move_{self.direction}")
        for i in range(1, self.num_tables + 1):
            log.info(f"--- Objeto {i}/{self.num_tables} (moviendo {self.direction}) ---")
            move_fn(self.table_distance_cm)

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

    # ---------- Modo manual: solo stream + YOLO, sin vuelo ----------

    def run_manual(self) -> bool:
        """Modo manual: conecta al dron, muestra su cámara con YOLO, NO vuela.

        El usuario carga el dron físicamente y lo apunta a los objetos.
        Útil cuando el vuelo autónomo falla por IMU/motores y solo se quiere
        demostrar la detección.
        """
        log.info("=== MODO MANUAL — el dron NO va a despegar ===")
        log.info("Carga el dron con tu mano y apunta su cámara a los objetos.")
        log.info("Presiona 'q' en la ventana de OpenCV para salir.")
        target_found = False
        try:
            self.ctrl.connect()
            bat = self.ctrl.get_battery()
            log.info(f"Batería: {bat}%")
            target_found = self._manual_loop()
        finally:
            self.ctrl.end()
            if self.show:
                cv2.destroyAllWindows()
        return target_found

    def _manual_loop(self) -> bool:
        """Lee frames, corre YOLO, muestra HUD. Devuelve True si vio el target."""
        target_seen = False
        last_log_time = 0.0
        while True:
            frame = self.ctrl.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            detections = self.det.detect(frame)
            hit = self.det.target_found(detections)

            if hit is not None:
                if not target_seen:
                    log.info(f"🎯 Primera detección de '{hit.label}' "
                             f"con conf={hit.conf:.2f}")
                    target_seen = True
                else:
                    now = time.time()
                    if now - last_log_time > 2.0:
                        log.info(f"  target visible: {hit.label} ({hit.conf:.2f})")
                        last_log_time = now

            if self.show:
                self._render_manual(frame, detections, hit)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # En modo headless el loop manual no tiene sentido; salimos rápido.
                break

        return target_seen

    # ---------- Modo teclado: control en vivo + YOLO sobre todas las clases ----------

    def run_keyboard(self, speed: int = 40) -> None:
        """Modo teclado: vuelo manual con flechas + WASD, YOLO detecta TODO.

        Controles:
            Flechas: adelante / atrás / izquierda / derecha
            W / S  : subir / bajar
            A / D  : rotar izq / der
            T      : takeoff
            L      : land
            +/-    : aumentar / reducir velocidad
            Espacio: emergency (corte motores)
            ESC    : salir (aterriza primero si está en vuelo)
        """
        from pynput import keyboard as kb  # lazy import: solo aquí

        state = {
            "lr": 0, "fb": 0, "ud": 0, "yaw": 0,
            "speed": speed,
            "request_takeoff": False,
            "request_land": False,
            "request_emergency": False,
            "request_quit": False,
        }

        def _key_attrs(key):
            name = getattr(key, "name", None)
            char = None
            ch = getattr(key, "char", None)
            if isinstance(ch, str) and ch:
                char = ch.lower()
            return name, char

        def on_press(key):
            name, char = _key_attrs(key)
            if   name == "up":    state["fb"] = state["speed"]
            elif name == "down":  state["fb"] = -state["speed"]
            elif name == "left":  state["lr"] = -state["speed"]
            elif name == "right": state["lr"] = state["speed"]
            elif char == "w":     state["ud"] = state["speed"]
            elif char == "s":     state["ud"] = -state["speed"]
            elif char == "a":     state["yaw"] = -state["speed"]
            elif char == "d":     state["yaw"] = state["speed"]
            elif char == "t":     state["request_takeoff"] = True
            elif char == "l":     state["request_land"] = True
            elif char in ("+", "="):
                state["speed"] = min(100, state["speed"] + 10)
            elif char in ("-", "_"):
                state["speed"] = max(10, state["speed"] - 10)
            elif name == "esc":   state["request_quit"] = True
            elif name == "space": state["request_emergency"] = True

        def on_release(key):
            name, char = _key_attrs(key)
            if   name in ("up", "down"):       state["fb"] = 0
            elif name in ("left", "right"):    state["lr"] = 0
            elif char in ("w", "s"):           state["ud"] = 0
            elif char in ("a", "d"):           state["yaw"] = 0

        listener = kb.Listener(on_press=on_press, on_release=on_release)
        listener.start()

        flying = False
        try:
            self.ctrl.connect()
            bat = self.ctrl.get_battery()
            log.info(f"Batería: {bat}%")
            log.info("=== MODO TECLADO — controles:")
            log.info("  Flechas: adelante/atrás/izq/der  |  W/S: subir/bajar  |  A/D: rotar")
            log.info("  T: takeoff  |  L: land  |  +/-: velocidad  |  ESC: salir  |  Espacio: emergency")

            loop_dt = 0.05  # 20 Hz, suficiente para RC y video
            while not state["request_quit"]:
                if state["request_emergency"]:
                    log.warning("EMERGENCY presionado — cortando motores")
                    self.ctrl.emergency()
                    flying = False
                    state["request_emergency"] = False
                    break

                if state["request_takeoff"] and not flying:
                    log.info("Takeoff solicitado")
                    self.ctrl.takeoff()
                    flying = True
                    state["request_takeoff"] = False

                if state["request_land"] and flying:
                    log.info("Land solicitado")
                    self.ctrl.land()
                    flying = False
                    state["request_land"] = False

                if flying:
                    self.ctrl.send_rc_control(
                        state["lr"], state["fb"], state["ud"], state["yaw"]
                    )

                frame = self.ctrl.get_frame()
                if frame is not None:
                    detections = self.det.detect(frame)
                    if self.show:
                        self._render_keyboard(frame, detections, state, flying)
                        # waitKey además mantiene la ventana viva
                        if cv2.waitKey(1) & 0xFF == 27:  # ESC en ventana
                            state["request_quit"] = True

                time.sleep(loop_dt)

            if flying:
                log.info("Quit solicitado — aterrizando")
                try:
                    self.ctrl.land()
                except Exception as e:
                    log.warning(f"land() falló: {e}; intentando emergency")
                    try: self.ctrl.emergency()
                    except Exception: pass
        finally:
            listener.stop()
            self.ctrl.end()
            if self.show:
                cv2.destroyAllWindows()

    def _render_keyboard(self, frame, detections, state, flying) -> None:
        """HUD del modo teclado: bboxes de TODO + estado de control + lista."""
        # Bounding boxes con color cian uniforme + label + %
        for d in detections:
            x1, y1, x2, y2 = (int(v) for v in d.bbox)
            color = (255, 200, 0)  # cian BGR
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label_text = f"{d.label} {d.conf * 100:.0f}%"
            cv2.putText(frame, label_text, (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        h, w = frame.shape[:2]

        # HUD superior: estado de vuelo + velocidad
        cv2.rectangle(frame, (0, 0), (w, 38), (0, 0, 0), -1)
        status = "EN VUELO" if flying else "EN PISO"
        status_color = (0, 255, 0) if flying else (0, 200, 255)
        cv2.putText(frame, f"{status}  |  vel={state['speed']}",
                    (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        # Lista de objetos detectados (sumarizada, max conf por clase)
        by_class: dict[str, float] = {}
        for d in detections:
            by_class[d.label] = max(by_class.get(d.label, 0.0), d.conf)
        if by_class:
            sorted_items = sorted(by_class.items(), key=lambda kv: -kv[1])
            top_items = sorted_items[:6]
            list_text = "  ".join(f"{lbl}:{c*100:.0f}%" for lbl, c in top_items)
            cv2.rectangle(frame, (0, 38), (w, 65), (30, 30, 30), -1)
            cv2.putText(frame, list_text, (10, 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # HUD inferior: instrucciones rápidas
        cv2.rectangle(frame, (0, h - 28), (w, h), (0, 0, 0), -1)
        cv2.putText(frame,
                    "Flechas mover | W/S subir-bajar | A/D rotar | T takeoff | L land | ESC salir",
                    (10, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        cv2.imshow("Tello YOLO - Teclado", frame)

    def _render_manual(self, frame, detections, target_hit) -> None:
        """Render con HUD para modo manual: target arriba, porcentajes en cada caja."""
        # Bounding boxes con porcentaje
        for d in detections:
            x1, y1, x2, y2 = (int(v) for v in d.bbox)
            is_target = d.label == self.det.target
            color = (0, 255, 0) if is_target else (255, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label_text = f"{d.label} {d.conf * 100:.0f}%"
            cv2.putText(frame, label_text, (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # HUD superior: estado del target
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w, 45), (0, 0, 0), -1)
        if target_hit is not None:
            hud = f"ENCONTRADO: {target_hit.label}  {target_hit.conf * 100:.0f}%"
            hud_color = (0, 255, 0)
        else:
            hud = f"BUSCANDO: {self.det.target}"
            hud_color = (0, 255, 255)
        cv2.putText(frame, hud, (10, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, hud_color, 2)

        # HUD inferior: instrucciones
        cv2.rectangle(frame, (0, h - 28), (w, h), (0, 0, 0), -1)
        cv2.putText(frame, "MODO MANUAL — presiona 'Q' para salir",
                    (10, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        cv2.imshow("Tello YOLO - Manual", frame)
