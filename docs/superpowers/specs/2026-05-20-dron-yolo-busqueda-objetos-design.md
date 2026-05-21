# Diseño: Búsqueda de objetos con dron Tello + YOLO

**Fecha**: 2026-05-20
**Autor**: Erik (UAQ — DCC — Optativa I)
**Estado**: Diseño aprobado, listo para plan de implementación

---

## 1. Resumen

Sistema en Python que controla un dron Ryze Tello para volar en línea recta sobre 6 mesas con 6 objetos distintos, detectar los objetos en tiempo real con YOLOv8 pre-entrenado (COCO) usando la cámara del dron, y detenerse (hover) sobre la mesa donde está un objeto objetivo indicado por el usuario antes del despegue.

El proyecto soporta dos modos: **simulación** (usa webcam o video pregrabado, no vuela) y **real** (vuela el Tello). Ambos modos comparten el mismo código de lógica/detección.

---

## 2. Objetivos y no-objetivos

### Objetivos
- Detectar 6 objetos sobre mesas usando YOLOv8n pre-entrenado en COCO.
- Vuelo autónomo lineal sobre las 6 mesas con escaneo en cada parada.
- Detener el dron (hover) sobre la mesa donde aparece el objeto objetivo.
- Modo simulación funcional sin el dron real.
- Aterrizaje seguro en cualquier estado de error.

### No-objetivos (fuera de scope)
- Detección de obstáculos / anti-colisión (el Tello no lo soporta nativamente).
- Reconocimiento de objetos fuera de COCO (sin entrenamiento custom).
- Comandos por voz, GUI gráfica, regreso automático al punto de origen.
- Vuelo en formaciones no lineales (curvas, círculos, zigzag).
- Detección continua durante el movimiento (visual servoing).

---

## 3. Requisitos

### Hardware
- Dron **Ryze Tello** (estándar, no EDU obligatorio).
- Laptop con WiFi (probado para ASUS Zenbook con Intel iGPU).
- 6 mesas alineadas en fila recta, separadas ~80 cm centro a centro.
- 1 objeto por mesa: refresco (botella), libro, taza, mochila, celular, mouse.
- Espacio aéreo despejado a 120 cm sobre las mesas.

### Software
- Python 3.10 o 3.11.
- Conexión a internet en la primera ejecución (descarga `yolov8n.pt`).
- Sistema operativo: Windows 11 (probado), macOS o Linux (compatibles).

---

## 4. Objetos a detectar y mapeo COCO

| Nombre usuario | Alias aceptados | Clase COCO |
|---|---|---|
| Refresco | `refresco`, `botella` | `bottle` |
| Libro | `libro` | `book` |
| Taza | `taza` | `cup` |
| Mochila | `mochila` | `backpack` |
| Celular | `celular`, `telefono` | `cell phone` |
| Mouse | `mouse`, `raton` | `mouse` |

El mapeo vive en `config.py` como `TARGET_ALIASES`. El CLI acepta cualquier alias y traduce internamente a la clase COCO. Si el usuario pasa un target inválido, el programa falla con mensaje claro **antes** de despegar.

---

## 5. Stack tecnológico

| Componente | Librería | Versión sugerida |
|---|---|---|
| Control del dron | `djitellopy` | ~=2.5 |
| Visión | `opencv-python` | ~=4.10 |
| Detección | `ultralytics` (YOLOv8) | ~=8.3 |
| Modelo | `yolov8n.pt` | nano, ~6 MB, COCO 80 clases |
| Python | stdlib (`argparse`, `logging`, `threading`, `time`) | 3.10/3.11 |

Sin GPU NVIDIA confirmada: el modelo nano corre en CPU a ~10-20 FPS, suficiente para escaneo en hover.

---

## 6. Arquitectura

**Enfoque elegido**: Monolítico secuencial (Enfoque A en el brainstorming).

Loop principal síncrono: despegar → para cada mesa, avanzar X cm → hover Y segundos → leer N frames → si target detectado en ≥K frames con conf≥umbral, detener; si no, siguiente mesa.

### Estructura de archivos

```
ProyectoFinalYOLO/
├── README.md
├── requirements.txt
├── config.py                    # constantes y aliases
├── main.py                      # entry point + CLI
├── mission.py                   # MissionPlanner
├── drone/
│   ├── __init__.py
│   ├── tello_controller.py      # wrapper djitellopy (vuelo real)
│   └── mock_controller.py       # webcam/video, no vuela
├── vision/
│   ├── __init__.py
│   └── detector.py              # YOLODetector
├── assets/
│   └── yolov8n.pt               # descargado en runtime
└── logs/                        # logs por sesión
```

### Decisiones clave de diseño

- **Interfaz polimórfica**: `TelloController` y `MockController` exponen los mismos métodos públicos. `main.py` instancia uno u otro según `--mode`. El resto del código nunca distingue entre ambos.
- **`MissionPlanner` agnóstico del hardware**: recibe `controller` y `detector` ya construidos. Es testeable sin dron ni modelo.
- **Constantes centralizadas en `config.py`**: altura, distancias, umbrales, K frames de confirmación. Un solo archivo para calibrar.
- **Sin abstracciones extras**: no hay capas de evento/state-machine. 6 archivos Python.

---

## 7. Flujo de la misión (alto nivel)

```python
# main.py (pseudocódigo)
args = parse_args()  # --mode sim|real, --target refresco, --tables 6, --show
controller = TelloController() if args.mode == "real" else MockController(args.video)
detector   = YOLODetector("yolov8n.pt", resolve_alias(args.target), CONF_THRESHOLD)
mission    = MissionPlanner(controller, detector, num_tables=args.tables, show=args.show)
mission.run()
```

### `MissionPlanner.run()` — paso a paso

1. **Preflight checks**: batería ≥30%, conexión al dron, stream de video activo, target válido.
2. Despegar y subir a `FLIGHT_HEIGHT_CM` (120 cm).
3. **Para cada mesa `i` en `1..num_tables`**:
   1. Avanzar `TABLE_DISTANCE_CM` (80 cm).
   2. Hover.
   3. Durante `SCAN_TIME_SEC` (2.5 s), leer hasta `SCAN_MAX_FRAMES` (15) frames del controller.
   4. Pasar cada frame al `YOLODetector`.
   5. Contar frames donde `target_found()` devuelve una detección.
   6. Si el conteo ≥ `CONFIRM_K_FRAMES` (3):
      - Log "🎯 Objetivo encontrado en mesa i".
      - Hover adicional `HOLD_TIME_SEC` (4 s).
      - Romper el loop.
   7. Verificar batería; si <15% → abort.
4. Si recorrió las 6 mesas sin encontrar → log "No se encontró el objetivo".
5. **Finally**: aterrizar.

### Parámetros de calibración (en `config.py`)

| Constante | Valor inicial | Notas |
|---|---|---|
| `FLIGHT_HEIGHT_CM` | 120 | Encima de mesas y cabezas. |
| `TABLE_DISTANCE_CM` | 80 | Centro a centro entre mesas. |
| `SCAN_TIME_SEC` | 2.5 | Tiempo de hover por mesa. |
| `SCAN_MAX_FRAMES` | 15 | Cap de frames a procesar por mesa. |
| `CONFIRM_K_FRAMES` | 3 | Frames con detección para confirmar. |
| `HOLD_TIME_SEC` | 4 | "Detención" sobre el objetivo. |
| `CONF_THRESHOLD` | 0.55 | Umbral de confianza YOLO. |
| `BATTERY_PREFLIGHT_MIN` | 30 | % mínimo para despegar. |
| `BATTERY_ABORT_MIN` | 15 | % donde aborta y aterriza. |

---

## 8. Módulo de detección

### `YOLODetector` (vision/detector.py)

```python
@dataclass
class Detection:
    label: str
    conf: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2

class YOLODetector:
    def __init__(self, model_path: str, target: str, conf_threshold: float):
        self.model = YOLO(model_path)
        self.target = target               # clase COCO ya resuelta
        self.conf_threshold = conf_threshold
        self._validate_target_in_coco()

    def detect(self, frame) -> list[Detection]:
        results = self.model(frame, verbose=False)[0]
        return [
            Detection(self.model.names[int(b.cls)], float(b.conf), tuple(b.xyxy[0].tolist()))
            for b in results.boxes
            if float(b.conf) >= self.conf_threshold
        ]

    def target_found(self, detections: list[Detection]) -> Detection | None:
        candidates = [d for d in detections if d.label == self.target]
        return max(candidates, key=lambda d: d.conf, default=None)
```

### Política de detección

- Confirmación **multi-frame**: solo se considera "encontrado" cuando ≥`CONFIRM_K_FRAMES` frames consecutivos del hover dan positivo. Evita falsos positivos puntuales.
- **Umbral alto** (0.55): el vuelo y la perspectiva degradan la confianza; valor alto evita ver "celular" cuando se está sobre "taza" en mesa adyacente.
- **Sin tracking** (DeepSORT/ByteTrack): el dron escanea casi quieto.
- **Visualización opcional** (`--show`): ventana OpenCV con frames + bboxes; útil para demo.

---

## 9. Modo simulación

### `MockController` (drone/mock_controller.py)

Implementa la misma interfaz pública que `TelloController`:

| Método | Comportamiento mock |
|---|---|
| `connect()` | Log + `return True` |
| `takeoff()` | Log + `sleep(1)` |
| `land()` | Log + `sleep(1)` |
| `move_forward(cm)` | Log + `sleep(cm/50)` (simula tiempo real) |
| `get_frame()` | Lee frame de webcam o video con `cv2.VideoCapture` |
| `get_battery()` | Devuelve constante 100 |
| `emergency()` | Log warning |
| `end()` | `cap.release()` |

### Fuentes de video soportadas

1. **Webcam**: `--video 0` (apuntas la cámara a los objetos manualmente).
2. **Video pregrabado**: `--video assets/sample_flight.mp4` (grabado caminando sobre las 6 mesas con el celular).
3. **Frame estático**: `--video assets/static_frame.jpg` (un solo frame, para depurar detección).

### Beneficios

- Desarrollo sin riesgo de chocar el dron.
- Reproducibilidad con videos pregrabados.
- Misma CLI: `--mode sim` vs `--mode real` es lo único que cambia.

---

## 10. Seguridad y manejo de errores

| Riesgo | Mitigación |
|---|---|
| Batería baja en vuelo | Chequeo preflight (≥30%) y dentro del loop (≥15%); aborta si <15%. |
| Pérdida WiFi con Tello | `TelloException` → handler aterriza si está en aire, log + exit. |
| Choque con obstáculo | **No hay anti-colisión**. Mitigación operativa: altura 120 cm y usuario despeja el espacio. |
| Inferencia YOLO se cuelga | Timeout 5 s en `detect()`; log warning y avanza a siguiente mesa. |
| Abort manual | Tecla `Q` en la ventana OpenCV → `emergency_land()`. Requiere `--show` activado (default True). |
| Falla genérica | `try/finally` en `run()`: el `finally` siempre llama `controller.land()`. Si falla → `controller.emergency()` (corta motores). |
| Stream de video no llega | 3 reintentos con backoff; si no, abort antes de despegar. |
| Modelo no descargado | Primer run requiere internet (~6 MB); README lo aclara. |

### Logging

Cada sesión escribe a `logs/flight_YYYY-MM-DD_HH-MM.log` con timestamps. Útil para post-mortem de demos en vivo.

---

## 11. CLI

```bash
# Modo simulación con webcam, buscar refresco
python main.py --mode sim --video 0 --target refresco --show

# Modo simulación con video pregrabado
python main.py --mode sim --video assets/sample_flight.mp4 --target mouse

# Modo real: vuela el Tello
python main.py --mode real --target libro --show

# Cambiar número de mesas (default 6)
python main.py --mode real --target celular --tables 4
```

### Argumentos

| Flag | Default | Descripción |
|---|---|---|
| `--mode` | `sim` | `sim` o `real`. |
| `--target` | (requerido) | Alias o nombre COCO del objeto a buscar. |
| `--video` | `0` | Solo en sim: webcam (int) o path de archivo. **Se ignora si `--mode real`.** |
| `--tables` | `6` | Número de mesas a recorrer. |
| `--show` | True | Abre ventana OpenCV con bboxes. Usa `--no-show` para desactivar. La ventana es además dónde se captura la tecla `Q` para abort. |

---

## 12. Plan de pruebas

### Unit tests (sin dron)
- `YOLODetector` con frame estático conocido (imagen de una taza) → detección esperada.
- `YOLODetector` con target inválido → `ValueError` antes del despegue.
- `MockController` ciclo completo (`connect → takeoff → move → land → end`) sin errores.
- `MissionPlanner` con `MockController` y `YOLODetector` mockeado → termina ordenadamente cuando se "encuentra" el objeto.

### Integración (modo sim)
- Correr `main.py --mode sim --video assets/sample_flight.mp4 --target libro` y verificar log de detección.
- Forzar batería baja en `MockController` (subclase de test) → confirmar abort.
- Forzar `KeyboardInterrupt` → confirmar aterrizaje.

### Vuelo real
- Test inicial con mesas vacías: que el dron recorra las 6 sin detectar nada y aterrice.
- Test con 1 objeto: que se detenga en la mesa correcta.
- Test con los 6 objetos colocados aleatoriamente: probar cada uno de los 6 targets.
- Test de abort: presionar `Q` durante el vuelo.

---

## 13. Riesgos del proyecto

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| YOLO no detecta el objeto desde 120 cm | Media | Alto | Bajar altura a 90 cm en calibración; objetos grandes (mochila, libro) están bien, los pequeños (mouse) son frontera. |
| Tello no avanza exactamente 80 cm (drift) | Alta | Medio | Hover suficientemente largo para que el escaneo cubra mesas adyacentes; cinta en el piso para alinear inicio. |
| WiFi del Tello inestable en aula con muchas redes | Media | Alto | Test en aula antes de la demo; tener un router 2.4 GHz limpio si es posible. |
| Confusión COCO entre `bottle` y `cup` (refresco vs taza) | Baja | Medio | Umbral 0.55 + confirmación 3 frames; en peores casos, ajustar disposición física. |
| Batería se acaba en demo (Tello ~10 min) | Media | Alto | Tener batería extra cargada; vuelo total estimado <2 min. |

---

## 14. Métricas de éxito

- Modo sim corre end-to-end sin errores con un video pregrabado.
- Vuelo real: en ≥3 de 5 intentos consecutivos, el dron se detiene sobre la mesa correcta del objeto solicitado.
- Aterrizaje seguro en el 100% de los casos (sin choques ni caídas).
- Demo de clase funciona sin reinicios manuales.

---

## 15. Próximos pasos (post-diseño)

1. Crear plan de implementación detallado paso a paso (skill `writing-plans`).
2. Ejecutar el plan: bootstrap del proyecto, modo sim primero, modo real después.
3. Calibrar en sitio con las mesas reales.
4. Demo.
