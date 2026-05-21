# Dron YOLO — Búsqueda de objetos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar sistema en Python que controla un dron Ryze Tello para volar sobre 6 mesas, detectar objetos con YOLOv8 + COCO, y detenerse (hover) sobre la mesa con el objeto objetivo solicitado por CLI.

**Architecture:** Monolítico secuencial. `main.py` instancia un controller (`TelloController` o `MockController` según `--mode`) y un `YOLODetector`, los pasa a `MissionPlanner.run()` que ejecuta el loop: takeoff → para cada mesa, avanzar y escanear → si encuentra, hover → aterrizar. Modo sim usa webcam/video sin volar; modo real usa djitellopy.

**Tech Stack:** Python 3.10+, `djitellopy` 2.5+, `ultralytics` (YOLOv8n), `opencv-python`, `pytest` para tests.

**Spec:** [docs/superpowers/specs/2026-05-20-dron-yolo-busqueda-objetos-design.md](../specs/2026-05-20-dron-yolo-busqueda-objetos-design.md)

---

## Resumen de archivos

| Archivo | Responsabilidad |
|---|---|
| `requirements.txt` | Dependencias pinned |
| `README.md` | Cómo instalar, correr, calibrar |
| `config.py` | Constantes (alturas, distancias, umbrales) + `TARGET_ALIASES` + `resolve_alias()` |
| `vision/detector.py` | `YOLODetector` + dataclass `Detection` |
| `drone/mock_controller.py` | `MockController` (webcam/video, no vuela) |
| `drone/tello_controller.py` | `TelloController` (wrapper djitellopy) |
| `mission.py` | `MissionPlanner` (loop de la misión) |
| `main.py` | CLI con argparse, wire-up de componentes |
| `tests/test_*.py` | Pruebas unitarias para cada módulo |

---

## Convenciones para todas las tareas

- **Trabajar desde**: `c:\Users\erikj\OneDrive\Documents\UAQ\DCC\Optativa I\ProyectoFinalYOLO`
- **Activar venv en cada terminal nueva**: `.venv\Scripts\activate` (Windows PowerShell)
- **Correr tests con**: `pytest -v` (desde la raíz del proyecto)
- **Commit después de cada tarea verde** (TDD: red → green → commit)
- **Mensajes de commit**: en español, formato `tipo: descripción corta` (feat, fix, docs, test, chore)

---

## Task 1: Bootstrap del proyecto

**Files:**
- Create: `requirements.txt`
- Create: `README.md`
- Create: `.python-version` (opcional, pero útil)
- Create: directorios `drone/`, `vision/`, `assets/`, `logs/`, `tests/`
- Create: `drone/__init__.py`, `vision/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Crear estructura de carpetas y archivos vacíos**

Desde la raíz del proyecto, en PowerShell:

```powershell
New-Item -ItemType Directory -Force drone, vision, assets, logs, tests | Out-Null
New-Item -ItemType File -Force drone/__init__.py, vision/__init__.py, tests/__init__.py | Out-Null
```

- [ ] **Step 2: Escribir `requirements.txt`**

```
djitellopy~=2.5
ultralytics~=8.3
opencv-python~=4.10
numpy~=1.26
pytest~=8.3
```

- [ ] **Step 3: Crear venv e instalar**

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Esperado: instalación completa sin errores. La primera vez tarda varios minutos (ultralytics + torch).

- [ ] **Step 4: Crear `README.md` inicial**

```markdown
# Proyecto Final YOLO — Búsqueda con dron Tello

Sistema que vuela un dron Ryze Tello sobre 6 mesas, detecta objetos con YOLOv8 (COCO) y se detiene sobre el objeto objetivo.

## Requisitos
- Python 3.10 o 3.11
- Dron Ryze Tello (modo real) o webcam (modo simulación)
- Windows / macOS / Linux

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

## Uso

```bash
# Simulación con webcam
python main.py --mode sim --target refresco

# Vuelo real con el Tello
python main.py --mode real --target libro
```

(Documentación completa al final del proyecto.)
```

- [ ] **Step 5: Verificar instalación de ultralytics**

```powershell
python -c "from ultralytics import YOLO; print('ultralytics OK')"
```

Esperado: `ultralytics OK`. Si falla, revisar instalación (Windows a veces requiere Visual C++ Build Tools).

- [ ] **Step 6: Commit**

```powershell
git add requirements.txt README.md drone/__init__.py vision/__init__.py tests/__init__.py
git commit -m "chore: bootstrap del proyecto (requirements, estructura, README inicial)"
```

> Nota: `.venv/`, `logs/` y `assets/*.pt` están en `.gitignore`; no se commitean.

---

## Task 2: `config.py` con constantes y aliases

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escribir test fallido para `resolve_alias`**

`tests/test_config.py`:

```python
import pytest
from config import resolve_alias, TARGET_ALIASES


def test_resolve_alias_known_spanish():
    assert resolve_alias("refresco") == "bottle"
    assert resolve_alias("libro") == "book"
    assert resolve_alias("taza") == "cup"
    assert resolve_alias("mochila") == "backpack"
    assert resolve_alias("celular") == "cell phone"
    assert resolve_alias("mouse") == "mouse"


def test_resolve_alias_case_insensitive():
    assert resolve_alias("REFRESCO") == "bottle"
    assert resolve_alias("Libro") == "book"


def test_resolve_alias_accepts_coco_class_directly():
    assert resolve_alias("bottle") == "bottle"
    assert resolve_alias("cell phone") == "cell phone"


def test_resolve_alias_unknown_raises():
    with pytest.raises(ValueError, match="termo"):
        resolve_alias("termo")


def test_target_aliases_has_six_objects():
    coco_classes = set(TARGET_ALIASES.values())
    assert coco_classes == {"bottle", "book", "cup", "backpack", "cell phone", "mouse"}
```

- [ ] **Step 2: Correr el test, debe fallar**

```powershell
pytest tests/test_config.py -v
```

Esperado: FAIL — `ModuleNotFoundError: No module named 'config'`.

- [ ] **Step 3: Escribir `config.py`**

```python
"""Constantes y aliases del proyecto."""

# ----- Vuelo -----
FLIGHT_HEIGHT_CM = 120        # Altura sobre el piso.
TABLE_DISTANCE_CM = 80        # Distancia centro a centro entre mesas.
SCAN_TIME_SEC = 2.5           # Hover por mesa para escanear.
SCAN_MAX_FRAMES = 15          # Cap de frames procesados por mesa.
HOLD_TIME_SEC = 4             # Tiempo de "detención" sobre el objetivo.

# ----- Batería -----
BATTERY_PREFLIGHT_MIN = 30    # % mínimo para despegar.
BATTERY_ABORT_MIN = 15        # % donde aborta y aterriza.

# ----- Detección -----
CONF_THRESHOLD = 0.55         # Umbral de confianza YOLO.
CONFIRM_K_FRAMES = 3          # Frames con detección para confirmar.

# ----- Misión -----
DEFAULT_NUM_TABLES = 6

# ----- Aliases español -> clase COCO -----
TARGET_ALIASES = {
    "refresco": "bottle",
    "botella":  "bottle",
    "libro":    "book",
    "taza":     "cup",
    "mochila":  "backpack",
    "celular":  "cell phone",
    "telefono": "cell phone",
    "mouse":    "mouse",
    "raton":    "mouse",
}

# Clases COCO que aceptamos directamente (las 6 + aliases ya incluidos arriba apuntan a estas)
_COCO_CLASSES_VALIDAS = {"bottle", "book", "cup", "backpack", "cell phone", "mouse"}


def resolve_alias(name: str) -> str:
    """Traduce alias en español a clase COCO. Acepta también la clase COCO directa.

    Lanza ValueError si el nombre no es reconocido.
    """
    key = name.strip().lower()
    if key in TARGET_ALIASES:
        return TARGET_ALIASES[key]
    if key in _COCO_CLASSES_VALIDAS:
        return key
    raise ValueError(
        f"Objeto desconocido: '{name}'. "
        f"Aliases válidos: {sorted(TARGET_ALIASES.keys())}. "
        f"O usa clase COCO directa: {sorted(_COCO_CLASSES_VALIDAS)}."
    )
```

- [ ] **Step 4: Correr tests, deben pasar**

```powershell
pytest tests/test_config.py -v
```

Esperado: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add config.py tests/test_config.py
git commit -m "feat: agrega config con constantes y resolve_alias"
```

---

## Task 3: `vision/detector.py` — YOLODetector

**Files:**
- Create: `vision/detector.py`
- Create: `tests/test_detector.py`
- Create: `tests/fixtures/bus.jpg` (imagen de prueba de ultralytics)

- [ ] **Step 1: Descargar imagen de prueba conocida**

```powershell
New-Item -ItemType Directory -Force tests/fixtures | Out-Null
python -c "from ultralytics.utils.downloads import safe_download; safe_download(url='https://ultralytics.com/images/bus.jpg', dir='tests/fixtures')"
```

Esperado: archivo `tests/fixtures/bus.jpg` (imagen con personas y autobús, parte del conjunto de ejemplos de Ultralytics).

> Nota: esta imagen NO se commitea (la dejamos en gitignore). Si falla el download, se puede usar cualquier foto local con un objeto COCO conocido.

- [ ] **Step 2: Agregar fixtures a gitignore**

Modificar `.gitignore`, agregar al final:

```
tests/fixtures/
```

- [ ] **Step 3: Escribir test fallido**

`tests/test_detector.py`:

```python
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
```

- [ ] **Step 4: Correr el test, debe fallar**

```powershell
pytest tests/test_detector.py -v
```

Esperado: FAIL — `ModuleNotFoundError: No module named 'vision.detector'`.

- [ ] **Step 5: Implementar `vision/detector.py`**

```python
"""YOLOv8 wrapper para detección de objetos COCO."""

from dataclasses import dataclass
from ultralytics import YOLO


@dataclass(frozen=True)
class Detection:
    label: str
    conf: float
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)


class YOLODetector:
    def __init__(self, model_path: str, target: str, conf_threshold: float):
        self.model = YOLO(model_path)
        self.target = target
        self.conf_threshold = conf_threshold
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
        candidates = [d for d in detections if d.label == self.target]
        return max(candidates, key=lambda d: d.conf, default=None)
```

- [ ] **Step 6: Correr tests, deben pasar**

```powershell
pytest tests/test_detector.py -v
```

Esperado: 5 passed. La primera vez tarda ~30 s porque YOLO descarga el modelo `yolov8n.pt` (~6 MB).

> El archivo `yolov8n.pt` se guarda en la raíz del proyecto. Está en `.gitignore` por el patrón `assets/*.pt`; pero como cae en la raíz, agreguemos también `yolov8n.pt` explícito.

- [ ] **Step 7: Actualizar `.gitignore` para incluir el modelo en raíz**

Agregar al `.gitignore`:

```
yolov8n.pt
*.pt
```

- [ ] **Step 8: Commit**

```powershell
git add vision/detector.py tests/test_detector.py .gitignore
git commit -m "feat: agrega YOLODetector con tests sobre imagen conocida"
```

---

## Task 4: `drone/mock_controller.py`

**Files:**
- Create: `drone/mock_controller.py`
- Create: `tests/test_mock_controller.py`

- [ ] **Step 1: Escribir test fallido**

`tests/test_mock_controller.py`:

```python
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
```

- [ ] **Step 2: Correr test, debe fallar**

```powershell
pytest tests/test_mock_controller.py -v
```

Esperado: FAIL — `ModuleNotFoundError: No module named 'drone.mock_controller'`.

- [ ] **Step 3: Implementar `drone/mock_controller.py`**

```python
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
```

- [ ] **Step 4: Correr tests, deben pasar**

```powershell
pytest tests/test_mock_controller.py -v
```

Esperado: 4 passed.

> Los `time.sleep(1)` en takeoff/land son intencionales pero hacen el test un poco lento (~3 s total). Es aceptable porque solo se ejecuta una vez por suite.

- [ ] **Step 5: Commit**

```powershell
git add drone/mock_controller.py tests/test_mock_controller.py
git commit -m "feat: agrega MockController con tests de ciclo de vida"
```

---

## Task 5: `drone/tello_controller.py` — controlador real

**Files:**
- Create: `drone/tello_controller.py`
- Create: `tests/test_tello_controller_interface.py`

> Este módulo NO se puede testear sin hardware. Solo verificamos que la interfaz pública sea idéntica a `MockController` para garantizar polimorfismo.

- [ ] **Step 1: Escribir test de paridad de interfaz**

`tests/test_tello_controller_interface.py`:

```python
"""Verifica que TelloController y MockController exponen los mismos métodos.

NO vuela el dron — solo inspecciona las clases.
"""
import inspect
from drone.mock_controller import MockController
from drone.tello_controller import TelloController


REQUIRED_METHODS = ["connect", "takeoff", "land", "move_forward",
                    "get_frame", "get_battery", "emergency", "end"]


def test_tello_controller_has_required_methods():
    for name in REQUIRED_METHODS:
        assert hasattr(TelloController, name), f"Falta {name}"
        assert callable(getattr(TelloController, name))


def test_signatures_match_mock():
    for name in REQUIRED_METHODS:
        mock_sig = inspect.signature(getattr(MockController, name))
        real_sig = inspect.signature(getattr(TelloController, name))
        assert list(mock_sig.parameters.keys()) == list(real_sig.parameters.keys()), \
            f"Firma de {name} no coincide: mock={mock_sig}, real={real_sig}"
```

- [ ] **Step 2: Correr test, debe fallar**

```powershell
pytest tests/test_tello_controller_interface.py -v
```

Esperado: FAIL — `ModuleNotFoundError: No module named 'drone.tello_controller'`.

- [ ] **Step 3: Implementar `drone/tello_controller.py`**

```python
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
```

- [ ] **Step 4: Correr tests, deben pasar**

```powershell
pytest tests/test_tello_controller_interface.py -v
```

Esperado: 2 passed.

> Nota: la firma de `__init__` en mock es `(video_source=0)` y en real `(video_source=None)`. Ambas aceptan un parámetro opcional con nombre `video_source` — el test solo verifica los **nombres** de parámetros, no los defaults. Si quisieras strict-strict, ajusta el test.

- [ ] **Step 5: Commit**

```powershell
git add drone/tello_controller.py tests/test_tello_controller_interface.py
git commit -m "feat: agrega TelloController con interfaz pareada a MockController"
```

---

## Task 6: `mission.py` — MissionPlanner (loop principal)

**Files:**
- Create: `mission.py`
- Create: `tests/test_mission.py`

- [ ] **Step 1: Diseñar el test con fake controller + fake detector**

`tests/test_mission.py`:

```python
"""Tests del MissionPlanner usando dobles de prueba ligeros."""
from unittest.mock import MagicMock

import numpy as np
import pytest

from mission import MissionPlanner
from vision.detector import Detection


class FakeController:
    """Devuelve un frame distinto por cada move_forward."""
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
    def move_forward(self, cm):
        self.calls.append(f"forward:{cm}")
        self.table_idx += 1
        self.frames_remaining = self.total_per_table
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
    # Avanzó 3 veces y aterrizó (sin completar las 6)
    forward_calls = [c for c in ctrl.calls if c.startswith("forward:")]
    assert len(forward_calls) == 3
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
    forward_calls = [c for c in ctrl.calls if c.startswith("forward:")]
    assert len(forward_calls) == 6
    assert "land" in ctrl.calls


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
```

- [ ] **Step 2: Correr test, debe fallar**

```powershell
pytest tests/test_mission.py -v
```

Esperado: FAIL — `ModuleNotFoundError: No module named 'mission'`.

- [ ] **Step 3: Implementar `mission.py`**

```python
"""Orquestador de la misión: takeoff -> scan por mesa -> hover -> land."""

import logging
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
        self.show = show

    def run(self) -> bool:
        """Ejecuta la misión. Devuelve True si encontró el objetivo."""
        found = False
        try:
            self._preflight()
            self.ctrl.takeoff()
            found = self._fly_mission()
        finally:
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

    def _fly_mission(self) -> bool:
        for i in range(1, self.num_tables + 1):
            log.info(f"--- Mesa {i}/{self.num_tables} ---")
            self.ctrl.move_forward(self.table_distance_cm)

            if self._scan_for_target(table_idx=i):
                log.info(f"🎯 Objetivo '{self.det.target}' encontrado en mesa {i}")
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

        while frames_seen < self.scan_max_frames and time.time() < deadline:
            frame = self.ctrl.get_frame()
            if frame is None:
                continue
            frames_seen += 1

            detections = self.det.detect(frame)
            hit = self.det.target_found(detections)
            if hit is not None:
                positives += 1
                log.info(f"  detección {positives}/{self.confirm_k_frames} "
                         f"(conf={hit.conf:.2f}) en mesa {table_idx}")

            if self.show:
                self._render(frame, detections)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    raise KeyboardInterrupt("Abort manual con 'q'")

            if positives >= self.confirm_k_frames:
                return True

        return False

    def _hold(self) -> None:
        log.info(f"Hover {self.hold_time_sec}s sobre el objetivo")
        time.sleep(self.hold_time_sec)

    def _battery_too_low(self) -> bool:
        bat = self.ctrl.get_battery()
        return bat < self.battery_abort_min

    def _render(self, frame, detections) -> None:
        for d in detections:
            x1, y1, x2, y2 = (int(v) for v in d.bbox)
            color = (0, 255, 0) if d.label == self.det.target else (255, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{d.label} {d.conf:.2f}", (x1, max(15, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        cv2.imshow("Tello YOLO", frame)
```

- [ ] **Step 4: Correr tests, deben pasar**

```powershell
pytest tests/test_mission.py -v
```

Esperado: 4 passed.

- [ ] **Step 5: Correr suite completa**

```powershell
pytest -v
```

Esperado: todos los tests previos siguen verdes.

- [ ] **Step 6: Commit**

```powershell
git add mission.py tests/test_mission.py
git commit -m "feat: agrega MissionPlanner con loop secuencial y tests"
```

---

## Task 7: `main.py` — CLI

**Files:**
- Create: `main.py`
- Create: `tests/test_main_cli.py`

- [ ] **Step 1: Escribir test del parser CLI**

`tests/test_main_cli.py`:

```python
import pytest
from main import build_parser, build_components


def test_parser_defaults():
    args = build_parser().parse_args(["--target", "refresco"])
    assert args.mode == "sim"
    assert args.target == "refresco"
    assert args.video == "0"
    assert args.tables == 6
    assert args.show is True


def test_parser_real_mode():
    args = build_parser().parse_args(["--mode", "real", "--target", "libro"])
    assert args.mode == "real"


def test_parser_no_show():
    args = build_parser().parse_args(["--target", "mouse", "--no-show"])
    assert args.show is False


def test_build_components_sim_mode_returns_mock(tmp_path, monkeypatch):
    import numpy as np
    # crear un jpg dummy con un cuadrado para que opencv lo abra
    import cv2
    img = (np.random.rand(100, 100, 3) * 255).astype("uint8")
    p = tmp_path / "test.jpg"
    cv2.imwrite(str(p), img)

    args = build_parser().parse_args(
        ["--mode", "sim", "--video", str(p), "--target", "refresco"]
    )
    ctrl, det = build_components(args)
    from drone.mock_controller import MockController
    from vision.detector import YOLODetector
    assert isinstance(ctrl, MockController)
    assert isinstance(det, YOLODetector)
    assert det.target == "bottle"  # alias resuelto
    ctrl.end()


def test_build_components_unknown_target_raises():
    args = build_parser().parse_args(["--target", "termo"])
    with pytest.raises(ValueError):
        build_components(args)
```

- [ ] **Step 2: Correr test, debe fallar**

```powershell
pytest tests/test_main_cli.py -v
```

Esperado: FAIL — `ModuleNotFoundError: No module named 'main'`.

- [ ] **Step 3: Implementar `main.py`**

```python
"""Entry point CLI del proyecto."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import config
from mission import MissionPlanner
from vision.detector import YOLODetector
from drone.mock_controller import MockController
from drone.tello_controller import TelloController


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Dron Tello busca objetos con YOLO")
    p.add_argument("--mode", choices=["sim", "real"], default="sim",
                   help="sim: usa webcam/video; real: vuela el Tello")
    p.add_argument("--target", required=True,
                   help="Objeto a buscar (refresco, libro, taza, mochila, celular, mouse)")
    p.add_argument("--video", default="0",
                   help="Solo en sim: '0' webcam o ruta a video/imagen. Ignorado en real.")
    p.add_argument("--tables", type=int, default=config.DEFAULT_NUM_TABLES,
                   help="Número de mesas (default 6)")
    p.add_argument("--show", dest="show", action="store_true", default=True,
                   help="Mostrar ventana OpenCV (default activado)")
    p.add_argument("--no-show", dest="show", action="store_false",
                   help="Desactivar ventana OpenCV")
    return p


def build_components(args: argparse.Namespace):
    target_coco = config.resolve_alias(args.target)

    if args.mode == "real":
        controller = TelloController()
    else:
        video_src = int(args.video) if args.video.isdigit() else args.video
        controller = MockController(video_source=video_src)

    detector = YOLODetector(
        model_path="yolov8n.pt",
        target=target_coco,
        conf_threshold=config.CONF_THRESHOLD,
    )
    return controller, detector


def setup_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = Path("logs") / f"flight_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info(f"Log: {log_path}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging()
    log = logging.getLogger("main")
    log.info(f"Args: {args}")

    try:
        controller, detector = build_components(args)
    except ValueError as e:
        log.error(f"Error de configuración: {e}")
        return 2

    mission = MissionPlanner(
        controller=controller,
        detector=detector,
        num_tables=args.tables,
        show=args.show,
    )

    try:
        found = mission.run()
    except KeyboardInterrupt:
        log.warning("Abort manual")
        return 130
    except Exception as e:
        log.exception(f"Falla en la misión: {e}")
        return 1

    return 0 if found else 3


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Correr tests, deben pasar**

```powershell
pytest tests/test_main_cli.py -v
```

Esperado: 5 passed.

- [ ] **Step 5: Smoke test manual con una imagen estática**

Crear una imagen de prueba con un objeto COCO:

```powershell
# Descargar imagen con una botella visible
python -c "from ultralytics.utils.downloads import safe_download; safe_download(url='https://ultralytics.com/images/bus.jpg', dir='assets')"
```

Correr la misión:

```powershell
python main.py --mode sim --video assets/bus.jpg --target person --tables 2 --no-show
```

Esperado: logs muestran "🎯 Objetivo 'person' encontrado en mesa 1" (la imagen tiene personas). Exit code 0.

- [ ] **Step 6: Commit**

```powershell
git add main.py tests/test_main_cli.py
git commit -m "feat: agrega CLI main.py con logging por sesión"
```

---

## Task 8: README completo y checklist de calibración

**Files:**
- Modify: `README.md`
- Create: `docs/CALIBRACION.md`

- [ ] **Step 1: Reescribir `README.md` con instrucciones completas**

```markdown
# Proyecto Final YOLO — Búsqueda con dron Tello

Sistema que vuela un dron Ryze Tello sobre 6 mesas, detecta objetos con YOLOv8 (COCO) y se detiene sobre la mesa donde está el objeto objetivo.

## Cómo funciona (resumen)

1. Pones 6 objetos sobre 6 mesas en fila recta: refresco, libro, taza, mochila, celular, mouse.
2. Corres `python main.py --mode real --target libro` (por ejemplo).
3. El dron despega, avanza sobre cada mesa, escanea con YOLO, y se detiene sobre la mesa donde está el libro.

## Requisitos

- Python 3.10 o 3.11
- Conexión a internet (primera vez, para descargar el modelo)
- WiFi disponible para conectarse al Tello (red `TELLO-XXXXX`)

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

### Modo simulación (sin dron)

```powershell
# Usando la webcam
python main.py --mode sim --video 0 --target refresco

# Usando un video pregrabado
python main.py --mode sim --video assets/mi_video.mp4 --target mouse

# Usando una imagen estática
python main.py --mode sim --video assets/mesa1.jpg --target libro
```

### Modo real (con el Tello)

1. Cargar la batería del Tello.
2. Encender el dron.
3. Conectar tu laptop al WiFi `TELLO-XXXXX` (sin contraseña).
4. Colocar las 6 mesas en línea recta separadas ~80 cm centro a centro.
5. Colocar el dron en el piso, alineado con la primera mesa (~80 cm antes de ella).
6. Correr:

```powershell
python main.py --mode real --target libro
```

### Argumentos del CLI

| Flag | Default | Descripción |
|---|---|---|
| `--mode` | `sim` | `sim` o `real` |
| `--target` | (requerido) | refresco, libro, taza, mochila, celular, mouse |
| `--video` | `0` | Solo en sim: webcam o archivo |
| `--tables` | `6` | Número de mesas |
| `--show` / `--no-show` | `--show` | Ventana OpenCV con bboxes |

### Abort de emergencia

En la ventana de OpenCV, presiona **`Q`** → el dron aterriza inmediatamente.

## Objetos soportados

Solo los 6 mapeados en `config.py::TARGET_ALIASES`. Si necesitas otros objetos, asegúrate de que sean clases COCO y agrégalos al diccionario.

## Tests

```powershell
pytest -v
```

## Calibración

Ver [docs/CALIBRACION.md](docs/CALIBRACION.md).

## Estructura

```
.
├── main.py               # Entry CLI
├── mission.py            # Lógica de la misión
├── config.py             # Constantes
├── drone/
│   ├── tello_controller.py
│   └── mock_controller.py
├── vision/
│   └── detector.py
├── tests/
└── docs/
```
```

- [ ] **Step 2: Crear `docs/CALIBRACION.md`**

```markdown
# Calibración para vuelo real

Antes de la demo en clase, calibra los siguientes valores en `config.py`:

## 1. Distancia entre mesas (`TABLE_DISTANCE_CM`)

- Mide la distancia centro-a-centro entre las mesas.
- Default: 80 cm. Si tus mesas son más anchas (1 m), pon 100.

## 2. Altura de vuelo (`FLIGHT_HEIGHT_CM`)

- Default: 120 cm. Debe ser:
  - Suficientemente alto para librar las cabezas de los objetos más altos.
  - Suficientemente bajo para que YOLO vea bien los objetos pequeños (mouse, celular).
- Si el mouse no se detecta bien, baja a 90 cm.

## 3. Umbral de confianza (`CONF_THRESHOLD`)

- Default: 0.55.
- Si YOLO no detecta objetos que sí están: bajar a 0.40.
- Si detecta cosas que no son (falsos positivos): subir a 0.65.

## 4. Confirmación multi-frame (`CONFIRM_K_FRAMES`)

- Default: 3.
- Si el sistema confunde mesas adyacentes: subir a 5.
- Si tarda demasiado en confirmar: bajar a 2.

## 5. Pre-vuelo

Antes de cada vuelo:
- [ ] Batería ≥ 50% (la chequea el código a partir de 30, pero da margen).
- [ ] Espacio libre encima de las mesas y a los lados.
- [ ] Dron alineado con la primera mesa.
- [ ] WiFi conectado al `TELLO-XXXXX`.
- [ ] Ventilador/A.C. apagado si genera corrientes de aire.
```

- [ ] **Step 3: Commit**

```powershell
git add README.md docs/CALIBRACION.md
git commit -m "docs: documenta uso completo y proceso de calibración"
```

---

## Task 9: Verificación final end-to-end (modo sim)

**Files:** ninguno (solo verificación)

- [ ] **Step 1: Correr la suite completa**

```powershell
pytest -v
```

Esperado: todos los tests pasan.

- [ ] **Step 2: Smoke test sim con video estático**

```powershell
python main.py --mode sim --video assets/bus.jpg --target person --tables 2 --no-show
```

Esperado:
- Log "Preflight checks..."
- Log "Mesa 1/2"
- Log "🎯 Objetivo 'person' encontrado en mesa 1"
- Log "Hover 4s sobre el objetivo"
- Log "[MOCK] land"
- Exit code 0

- [ ] **Step 3: Smoke test sim con webcam**

Coloca uno de los 6 objetos frente a la webcam y corre:

```powershell
python main.py --mode sim --video 0 --target taza --tables 3
```

Esperado: aparece ventana OpenCV, el código avanza por las "mesas", confirma detección cuando ve la taza. Presiona `Q` para terminar antes de tiempo si quieres.

- [ ] **Step 4: Verificar logs**

```powershell
ls logs/
```

Esperado: archivos `flight_YYYY-MM-DD_HH-MM.log` con timestamps de cada ejecución.

- [ ] **Step 5: Commit final del estado de demo-ready**

Si quedan archivos sin commit (por ejemplo `assets/bus.jpg` está gitignored), no hace falta commit. Solo verifica:

```powershell
git status
git log --oneline
```

Esperado: working tree limpio, ~7-9 commits totales.

---

## Task 10 (opcional): Vuelo real

> Esta tarea se ejecuta solo cuando tengas el Tello disponible. Requiere supervisión humana — no es una tarea agentic.

- [ ] **Paso 1: Test sin objetos (recorrido limpio)**

Pon el dron, vacía las mesas y corre:

```powershell
python main.py --mode real --target libro --tables 6
```

Esperado: despega, recorre las 6 mesas, no encuentra nada, aterriza. Exit code 3.

- [ ] **Paso 2: Test con un solo objeto**

Pon un libro en la mesa 3. Corre el mismo comando.

Esperado: se detiene en la mesa 3, hover 4 s, aterriza. Exit code 0.

- [ ] **Paso 3: Test con los 6 objetos**

Coloca los 6 objetos en orden cualquiera. Prueba con los 6 targets uno por uno.

Anota qué objetos detecta bien y cuáles requieren ajuste de altura / umbral. Aplica cambios en `config.py` según [docs/CALIBRACION.md](docs/CALIBRACION.md).

- [ ] **Paso 4: Demo final**

Una vez calibrado, la demo de clase es: cargar batería al 80%+, encender Tello, conectar WiFi, correr `python main.py --mode real --target <objeto>` y mostrar el vuelo. Tener una batería de repuesto si la demo es larga.

---

## Notas de auto-revisión

Cobertura del spec:
- §3 Requisitos → Task 1 (deps)
- §4 Objetos / aliases → Task 2 (config) ✓
- §5 Stack → Task 1 (requirements) ✓
- §6 Arquitectura → todas las tasks reflejan la estructura ✓
- §7 Flujo de misión → Task 6 ✓
- §8 Detector → Task 3 ✓
- §9 Modo sim → Task 4 (MockController) + Task 7 (CLI) ✓
- §10 Seguridad → Task 6 (try/finally, batería) ✓
- §11 CLI → Task 7 ✓
- §12 Plan de pruebas → unit tests en cada Task + Task 9 integración + Task 10 vuelo ✓
- §13 Riesgos → mitigaciones en CALIBRACION.md (Task 8) ✓
- §14 Métricas → cubiertas en Task 9 y 10 ✓

Sin placeholders, sin TBD. Tipos consistentes (`Detection` definido una vez en Task 3, usado tal cual en Tasks 6 y 7).
