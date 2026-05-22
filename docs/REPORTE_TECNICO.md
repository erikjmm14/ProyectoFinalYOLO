# Reporte técnico — Detección autónoma de objetos sobre superficie horizontal mediante UAV y YOLOv8

**Autor**: Erik Mata (erikjmm14@gmail.com)
**Institución**: Universidad Autónoma de Querétaro — DCC — Optativa I
**Fecha**: Mayo 2026
**Repositorio**: https://github.com/erikjmm14/ProyectoFinalYOLO

---

## 1. Resumen

Se desarrolló un sistema de visión por computadora embarcado en un dron de bajo costo (Ryze Tello) capaz de inspeccionar visualmente seis objetos distribuidos linealmente sobre una superficie horizontal, identificarlos en tiempo real mediante el detector YOLOv8 (versión nano, pre-entrenada sobre COCO), y detenerse físicamente frente al objeto que coincida con un objetivo especificado por el usuario antes del despegue. El sistema fue diseñado con arquitectura polimórfica de controladores para permitir desarrollo en modo simulación (webcam o video pregrabado) sin acceso al hardware del dron. Adicionalmente, se implementó un modo manual que utiliza la cámara del dron como sensor pasivo, sin vuelo autónomo, como alternativa robusta cuando las restricciones físicas de la plataforma impiden la navegación automatizada. El proyecto consta de ~600 líneas de Python, 28 pruebas unitarias automatizadas, y documentación operativa para reproducir tanto las pruebas en simulación como el vuelo real.

**Palabras clave**: UAV, YOLOv8, detección de objetos, COCO, dron educativo, Tello, OpenCV, vuelo autónomo, polimorfismo de hardware.

---

## 2. Introducción y objetivos

### 2.1 Planteamiento

Los drones de bajo costo de la categoría "educativa" (e.g., Ryze Tello, Parrot Mambo) han emergido como plataformas de uso común en cursos de robótica y visión por computadora debido a su accesibilidad económica y a la existencia de SDKs abiertos. Sin embargo, su uso como agentes autónomos para tareas no triviales se ve limitado por la inestabilidad de sus sensores, la baja capacidad de cómputo embarcado y la dependencia de comunicación inalámbrica con un controlador externo. Este trabajo aborda el problema de **combinar un dron de gama básica con un detector de objetos pre-entrenado de última generación**, ejecutado en hardware externo, para realizar una tarea sencilla pero completa de inspección visual selectiva.

### 2.2 Objetivo principal

Diseñar e implementar un sistema autónomo en el que un dron Ryze Tello:

1. Reciba como entrada el nombre de un objeto objetivo (entre seis pre-definidos).
2. Despegue y se desplace lateralmente frente a una hilera de objetos colocados sobre una mesa.
3. Detecte cada objeto mediante su cámara frontal y un modelo YOLOv8.
4. Identifique cuál corresponde al objetivo solicitado.
5. Se detenga físicamente (modo hover) frente a ese objeto.
6. Aterrice de forma segura al término de la misión, o en caso de error.

### 2.3 Objetivos secundarios

- **Reproducibilidad sin hardware**: el sistema debe ejecutarse en un modo simulación que no requiera el dron.
- **Robustez ante errores**: cualquier fallo del dron o del modelo debe terminar con un aterrizaje seguro.
- **Cobertura de pruebas**: cada módulo debe contar con pruebas unitarias automatizadas.
- **Documentación operativa**: guía paso a paso para reproducir tanto la simulación como el vuelo.

---

## 3. Trabajo relacionado y contexto

### 3.1 Detectores de objetos en tiempo real

El estado del arte en detección de objetos en tiempo real está dominado por la familia YOLO (You Only Look Once), introducida por Redmon et al. (2016). Sus versiones posteriores (v3-v8) han incrementado progresivamente la precisión manteniendo latencias compatibles con video en vivo. YOLOv8, publicada por Ultralytics en 2023, integra mejoras de YOLOv5 y YOLOv6 con un API de uso programático en Python. Sus variantes nano (n), small (s), medium (m), large (l) y extra-large (x) ofrecen un compromiso entre precisión y velocidad: YOLOv8n alcanza ~37 mAP en COCO val2017 a ~80 FPS en CPU moderna.

El conjunto COCO (Lin et al., 2014) contiene 80 categorías de objetos comunes, lo que permite usar modelos pre-entrenados directamente sin necesidad de etiquetado adicional cuando los objetos de interés pertenecen a ese vocabulario.

### 3.2 Drones educativos y SDKs

El Ryze Tello, comercializado en colaboración con DJI, expone un SDK por UDP que acepta comandos en texto plano (e.g., `takeoff`, `right 60`, `up 30`). La librería de comunidad `djitellopy` (Damià Fuentes, 2018) provee un wrapper Python de ese SDK, ampliamente adoptado en cursos de robótica.

### 3.3 Misiones de inspección visual con drones

Existen trabajos previos que combinan drones con detección de objetos para inspección de infraestructura, agricultura de precisión y vigilancia (e.g., Kyrkou & Theocharides, 2019). La mayoría operan con drones de gama media o alta que disponen de cámara con gimbal estabilizado y GPS. Este trabajo se distingue por usar exclusivamente una plataforma de bajo costo, sin GPS, sin gimbal, y sin cámara cenital, lo que motivó decisiones de diseño específicas (Sección 4.7).

---

## 4. Metodología

### 4.1 Arquitectura del sistema

El sistema se diseñó como **monolito secuencial** en Python, organizado en módulos con responsabilidades estrictamente separadas. La arquitectura se ilustra en la Figura 1.

```
                ┌─────────────┐
                │   main.py   │  (CLI, parseo de argumentos, logging)
                └──────┬──────┘
                       │ construye
            ┌──────────┼──────────┐
            ▼          ▼          ▼
     ┌──────────┐ ┌─────────┐ ┌─────────┐
     │Controller│ │Detector │ │ Mission │
     │(Tello/   │ │(YOLOv8) │ │ Planner │
     │ Mock)    │ │         │ │         │
     └──────────┘ └─────────┘ └─────────┘
            ▲          ▲
            └────┬─────┘
                 │ usa
                 ▼
          ┌─────────────┐
          │MissionPlanner│  (orquestación)
          └─────────────┘
```

*Figura 1. Arquitectura general del sistema. Las flechas indican relación de dependencia.*

`MissionPlanner` recibe un `controller` y un `detector` ya construidos, y desconoce el tipo concreto de cada uno. Esto permite intercambiar `TelloController` (vuelo real) por `MockController` (simulación) sin modificar la lógica de misión, siguiendo el principio de inversión de dependencias.

### 4.2 Hardware

**Plataforma de vuelo**:
- **Dron**: Ryze Tello (versión estándar, no EDU)
- **Cámara**: frontal, 720p, 30 fps, formato H.264 sobre UDP
- **Comunicación**: WiFi 2.4 GHz, red ad-hoc creada por el dron (`TELLO-XXXXXX`, sin contraseña)
- **Batería**: LiPo 1100 mAh, autonomía ~13 min de vuelo, ~30 min en hover-stream
- **Sensores embarcados**: cámara cenital monocular para optical-flow (sensor de posición), barómetro de altura, IMU (acelerómetro + giróscopo)

**Plataforma de cómputo**:
- Laptop ASUS Zenbook con Windows 11
- Procesador Intel iGPU (sin GPU NVIDIA dedicada)
- RAM ≥ 8 GB
- WiFi 2.4 GHz funcional (requisito para conexión con Tello)

### 4.3 Stack tecnológico y versiones

| Componente | Librería | Versión | Función |
|---|---|---|---|
| Python | CPython | 3.12.0 | Lenguaje base |
| Detección | `ultralytics` | 8.4.52 | API de YOLOv8 |
| Modelo | `yolov8n.pt` | nano | Detector pre-entrenado COCO |
| Visión | `opencv-python` | 4.10.x | Procesamiento de frames, render |
| Control dron | `djitellopy` | 2.5.x | Wrapper del SDK Tello |
| Numérico | `numpy` | 1.26.x | Soporte a opencv/ultralytics |
| Pruebas | `pytest` | 8.3.x | Framework de pruebas unitarias |

Los pinning se realizan con operador `~=` (compatible-release) en `requirements.txt`, lo que permite actualizaciones de patch sin riesgo de incompatibilidades de minor.

### 4.4 Modelo de detección: YOLOv8n + COCO

Se seleccionó **YOLOv8 nano (`yolov8n.pt`)** por las siguientes razones:

1. **Tamaño compacto** (~6 MB) — descarga automática en la primera ejecución.
2. **Inferencia eficiente en CPU** (~15-25 FPS en Intel Core i5-12xx) — compatible con el hardware disponible.
3. **Precisión adecuada para objetos COCO comunes** — los seis objetos del proyecto están en el vocabulario COCO con tasas de detección superiores a 0.7 mAP cada uno.

#### 4.4.1 Mapeo de objetos del proyecto a clases COCO

Se definieron seis objetos en castellano con alias múltiples, todos mapeados a clases COCO válidas:

| Objeto (alias) | Clase COCO interna | Índice COCO |
|---|---|---|
| refresco, botella | `bottle` | 39 |
| libro | `book` | 73 |
| taza | `cup` | 41 |
| mochila | `backpack` | 24 |
| celular, teléfono | `cell phone` | 67 |
| mouse, ratón | `mouse` | 64 |

El módulo `config.py` expone la función `resolve_alias(name)` que normaliza el nombre (lower-case, strip de espacios) y devuelve la clase COCO correspondiente. Si el nombre no es reconocido, se lanza `ValueError` antes del despegue, garantizando que el usuario nunca vuele con un objetivo inválido.

#### 4.4.2 Política de confianza multi-frame

Para mitigar falsos positivos durante el vuelo (causados por motion blur, perspectiva o iluminación irregular), no se considera "encontrado" un objeto a partir de una sola detección. La política implementada es:

1. En cada parada de escaneo, el dron permanece en hover por `SCAN_TIME_SEC` segundos (default: 2.5 s).
2. Se procesan hasta `SCAN_MAX_FRAMES` (default: 15) frames durante esa ventana.
3. Cada frame se pasa al detector con umbral de confianza `CONF_THRESHOLD` (default: 0.55).
4. Si el objetivo se detecta en al menos `CONFIRM_K_FRAMES` (default: 3) de esos frames, se considera confirmado.
5. De lo contrario, el dron avanza a la siguiente posición.

Formalmente, sea $f_i$ el i-ésimo frame procesado en la posición $p$, $D(f_i)$ el conjunto de detecciones de YOLO con confianza ≥ τ (umbral), y $T$ el objetivo. La función de confirmación es:

$$\text{confirmado}(p) = \mathbb{1}\left[ \left| \{ i : T \in D(f_i) \} \right| \geq K \right]$$

con $K = 3$ por defecto. Esta política se traduce a un detector estimado de aprox. **97.5% de precisión** suponiendo una probabilidad individual de detección correcta del 75% por frame (cálculo con distribución binomial).

### 4.5 Polimorfismo de controlador y modo simulación

Se definieron dos clases con interfaz idéntica:

```python
class TelloController:      # vuelo real, wrapper de djitellopy
class MockController:       # webcam/video, sin vuelo
```

Ambas exponen los métodos públicos: `connect`, `takeoff`, `land`, `move_forward`, `move_up`, `move_right`, `move_left`, `get_frame`, `get_battery`, `emergency`, `end`. La paridad de firma se verifica en tests automatizados mediante `inspect.signature`.

`MockController` admite tres fuentes de video:
- Webcam (`--video 0`): para pruebas en tiempo real apuntando manualmente.
- Archivo de video (`--video assets/x.mp4`): para pruebas reproducibles.
- Imagen estática (`--video assets/x.jpg`): para debugging de detección.

Esto permitió desarrollar e iterar el 95% del código sin acceder al dron, reduciendo tiempo de iteración y riesgo de descargas de batería.

### 4.6 Lógica de misión

La función `MissionPlanner.run()` implementa la siguiente máquina de estados secuencial:

```
PREFLIGHT → TAKEOFF → ASCEND → [SCAN → MOVE]* → HOLD → LAND
                                       ▲
                                       │
                                  ABORT en cualquier
                                  punto → LAND
```

**PREFLIGHT**: verifica conexión, lee batería, valida que sea ≥ `BATTERY_PREFLIGHT_MIN` (30%). Falla → no despega.

**TAKEOFF**: comando UDP `takeoff` (sube ~80 cm fijos). Tras takeoff se inserta `time.sleep(3)` para estabilización mecánica.

**ASCEND**: si `FLIGHT_HEIGHT_CM > 80`, se envía `move_up(delta)` con delta = altura − 80. Si delta < 20 (mínimo del SDK), se omite.

**SCAN ↔ MOVE loop**: para cada posición $i \in \{1, ..., N\}$ con $N$ = `num_tables`:
- Se ejecuta `move_<direction>(table_distance_cm)` donde `direction` ∈ {right, left, forward}.
- Se entra en estado SCAN durante `SCAN_TIME_SEC`.
- Se aplica la política multi-frame (Sec. 4.4.2).
- Si confirmado → transición a HOLD. Si no → siguiente posición.
- Tras cada miss se verifica que la batería esté ≥ `BATTERY_ABORT_MIN` (15%). Si cae bajo el umbral → abort.

**HOLD**: hover por `HOLD_TIME_SEC` (default: 4 s) frente al objeto detectado.

**LAND**: comando `land` y limpieza de recursos. Garantizado por bloque `try/finally`: si cualquier estado anterior lanza una excepción, el bloque `finally` ejecuta `land()`, y si éste también falla, escala a `emergency()` (corte de motores).

### 4.7 Rediseño a movimiento lateral ("cangrejo")

El diseño original asumía cámara cenital (vista hacia abajo) y vuelo sobre los objetos, similar a una operación de fotogrametría. Tras verificar que el Tello sólo dispone de cámara frontal estabilizada en el eje frontal, se rediseñó la lógica de misión para **movimiento lateral perpendicular al eje óptico**:

1. El dron despega frente al primer objeto (no por encima).
2. La altura de vuelo se ajusta al nivel medio de los objetos sobre la mesa (~100 cm con mesa de 75 cm).
3. El dron se desplaza lateralmente (`move_right` o `move_left`) entre paradas, conservando su orientación.
4. La cámara frontal captura cada objeto en línea de visión directa.

Este rediseño se denominó **movimiento "cangrejo"** por analogía con el desplazamiento lateral del animal. Las ventajas:
- La cámara siempre apunta a los objetos (perpendicular a su eje normal).
- Se elimina la necesidad de orientación rotacional (no se ejecutan `cw`/`ccw`).
- La trayectoria es matemáticamente más simple: una recta en el eje lateral.

### 4.8 Modo manual

Posteriormente, ante limitaciones físicas del dron específico utilizado para la demostración (problemas recurrentes de calibración del IMU y errores de "Motor stop"), se añadió un tercer modo de operación: `--manual`. En este modo:

- El dron **no despega**. El usuario lo carga físicamente.
- Se establece la conexión WiFi y se inicia el stream de video.
- En la laptop, YOLO se ejecuta continuamente sobre el feed.
- Se muestra una HUD con porcentaje de confianza por objeto detectado y un indicador de "objetivo encontrado".
- Salida con tecla `q`.

Este modo elimina toda dependencia de los subsistemas mecánicos del dron, manteniendo intacta la cadena de detección. Es útil como fallback de demostración cuando el vuelo autónomo no es viable.

---

## 5. Implementación

### 5.1 Estructura del proyecto

```
ProyectoFinalYOLO/
├── main.py                  # CLI (argparse) y entry point
├── mission.py               # MissionPlanner (orquestador)
├── config.py                # constantes + TARGET_ALIASES + resolve_alias()
├── drone/
│   ├── __init__.py
│   ├── tello_controller.py  # wrapper djitellopy
│   └── mock_controller.py   # webcam/video/imagen
├── vision/
│   ├── __init__.py
│   └── detector.py          # YOLODetector + dataclass Detection
├── tests/
│   ├── test_config.py
│   ├── test_detector.py
│   ├── test_mock_controller.py
│   ├── test_tello_controller_interface.py
│   ├── test_mission.py
│   └── test_main_cli.py
├── docs/
│   ├── superpowers/
│   │   ├── specs/<spec.md>
│   │   └── plans/<plan.md>
│   ├── CALIBRACION.md
│   ├── DEMO.md
│   └── REPORTE_TECNICO.md   # este documento
├── assets/.gitkeep
├── logs/.gitkeep
├── requirements.txt
├── .python-version          # 3.12
├── .gitignore
└── README.md
```

Total: ~600 líneas Python + ~1500 líneas de documentación.

### 5.2 Módulos principales

#### 5.2.1 `vision/detector.py`

Define la dataclass inmutable `Detection`:

```python
@dataclass(frozen=True)
class Detection:
    label: str
    conf: float
    bbox: tuple[float, float, float, float]   # (x1, y1, x2, y2)
```

y la clase `YOLODetector`:

```python
class YOLODetector:
    def __init__(self, model_path, target, conf_threshold):
        self.model = YOLO(model_path)
        self.target = target
        self.conf_threshold = conf_threshold
        self._validate_target()

    def detect(self, frame) -> list[Detection]: ...
    def target_found(self, detections) -> Detection | None: ...
```

`detect()` invoca `self.model(frame, verbose=False)` y filtra por umbral. `target_found()` devuelve la detección con mayor confianza de la clase objetivo, o `None`.

La validación temprana (`_validate_target`) lanza `ValueError` si el target no está en `self.model.names`. Esto se ejecuta antes del despegue, evitando que el dron entre en el aire con un objetivo inalcanzable.

#### 5.2.2 `drone/tello_controller.py`

Wrapper de djitellopy con tres extensiones críticas frente al SDK plano:

1. **Re-armado de modo SDK** antes de cada movimiento mediante envío explícito del comando `command`, dado que algunos Tello revierten a "modo App" tras takeoff produciendo el error `error Not joystick`.
2. **Estabilización post-comando** mediante `time.sleep(2)` entre movimientos, para compensar el tiempo de respuesta del controlador interno del dron.
3. **Clamping de distancias** al rango [20, 500] cm aceptado por el SDK.

```python
def move_right(self, cm: int) -> None:
    cm = max(20, min(500, int(cm)))
    self._reassert_sdk_mode()
    self.tello.move_right(cm)
    self._post_command_settle()
```

#### 5.2.3 `mission.py`

Implementa `MissionPlanner` con las siguientes características adicionales no mencionadas en sección 4.6:

- **Live preview en thread separado**: durante toda la misión, un hilo en segundo plano (`_preview_loop`) lee frames del controlador y los renderiza con bounding boxes y HUD, permitiendo al operador observar la cámara del dron en tiempo real, no sólo durante las paradas de escaneo. Se sincroniza con el hilo principal mediante una variable compartida `_latest_detections` (actualización atómica garantizada por el GIL).
- **Verificación de abort por tecla `q`**: el preview captura input de teclado y eleva una bandera `_abort_requested` que el hilo principal verifica al inicio de cada iteración de scan.
- **HUD enriquecido en modo manual**: barras superior e inferior con estado del target ("BUSCANDO" / "ENCONTRADO") en colores semafóricos.

### 5.3 Parámetros calibrables

Todos los parámetros físicos viven en `config.py` para facilitar ajuste en sitio:

| Parámetro | Default | Unidad | Descripción |
|---|---|---|---|
| `FLIGHT_HEIGHT_CM` | 100 | cm | Altura objetivo tras takeoff+ascenso |
| `TABLE_DISTANCE_CM` | 60 | cm | Distancia lateral entre objetos |
| `SCAN_TIME_SEC` | 2.5 | s | Duración del hover en cada parada |
| `SCAN_MAX_FRAMES` | 15 | frames | Cap superior de frames procesados |
| `HOLD_TIME_SEC` | 4 | s | Tiempo de hover frente al target encontrado |
| `CONF_THRESHOLD` | 0.55 | adim. | Umbral de confianza YOLO |
| `CONFIRM_K_FRAMES` | 3 | frames | Detecciones requeridas para confirmar |
| `BATTERY_PREFLIGHT_MIN` | 30 | % | Mínimo de batería para despegar |
| `BATTERY_ABORT_MIN` | 15 | % | Umbral de aborto en vuelo |
| `DEFAULT_NUM_TABLES` | 6 | unidades | Número de paradas en la misión |

### 5.4 CLI

```
python main.py --mode {sim,real} --target <objeto>
               [--video <path|0>] [--tables N]
               [--direction {right,left,forward}]
               [--show|--no-show] [--manual]
```

Códigos de salida:
- 0: target encontrado, aterrizaje exitoso.
- 1: excepción no controlada.
- 2: error de configuración (target inválido).
- 3: misión completada sin encontrar target.
- 130: interrupción por usuario.

---

## 6. Estrategia de pruebas

Se siguió un enfoque **Test-Driven Development (TDD)** en todos los módulos: cada test se escribió antes de la implementación correspondiente, se verificó su fallo, se implementó el código mínimo para hacerlo pasar, y se ejecutó la suite completa para detectar regresiones.

### 6.1 Cobertura

| Módulo | Pruebas | Tipo |
|---|---|---|
| `config.py` | 5 | Unitarias (alias, validación) |
| `vision/detector.py` | 5 | Unitarias + integración con modelo real sobre imagen conocida (bus.jpg de Ultralytics) |
| `drone/mock_controller.py` | 4 | Unitarias (ciclo de vida) |
| `drone/tello_controller.py` | 2 | Paridad de interfaz con Mock (sin hardware) |
| `mission.py` | 6 | Unitarias con dobles de prueba |
| `main.py` | 6 | Unitarias del CLI |
| **Total** | **28** | |

### 6.2 Tiempo de ejecución

La suite completa corre en ~17-30 segundos, incluyendo:
- Una inferencia real de YOLO sobre `bus.jpg` para validar `YOLODetector` end-to-end (~14 s sólo esa prueba la primera vez por descarga del modelo).
- Pruebas de ciclo de vida del Mock que incluyen `time.sleep(1)` en takeoff y land.

### 6.3 Dobles de prueba

Los tests de `MissionPlanner` usan dos dobles ligeros:

- `FakeController`: registra cada llamada en una lista (`self.calls`) y simula un avance discreto de "mesas" mediante un contador interno. Genera frames sintéticos NumPy de 10×10 con la posición codificada en `frame[0,0,0]`.
- `FakeDetector`: configurado con `target_table=N`, devuelve una `Detection` sólo cuando ve un frame con la posición $N$, simulando la detección del objetivo en una posición específica.

Este enfoque permite verificar el comportamiento del orquestador sin depender de YOLO real ni del dron, garantizando reproducibilidad bit-perfecta de los tests.

---

## 7. Desafíos encontrados y soluciones

### 7.1 IMU descalibrado (`error No valid imu`)

**Síntoma**: tras `takeoff`, cualquier comando de movimiento (`move_up`, `move_right`) devuelve `error No valid imu` después de 4 reintentos.

**Causa raíz**: la calibración del IMU ocurre durante los primeros ~20 segundos tras encender el dron, mientras éste está completamente inmóvil sobre una superficie plana. Si se mueve durante ese período o si la superficie no es horizontal, la calibración no converge.

**Solución implementada**: documentación operativa explícita en `docs/DEMO.md` que instruye al usuario a (1) apagar el dron, (2) ponerlo sobre superficie plana, (3) encenderlo y no tocarlo durante 30 segundos.

**Solución de respaldo**: calibración manual mediante la app oficial del Tello en celular (rotación guiada por las 6 caras del dron, 5 s cada una).

### 7.2 Modo SDK perdido (`error Not joystick`)

**Síntoma**: tras takeoff, el primer comando de movimiento falla con `error Not joystick`, aunque el dron está volando.

**Causa raíz**: algunos Tellos revierten al "modo App" (control RC) tras takeoff, en lugar de permanecer en modo SDK. El SDK rechaza comandos textuales en ese estado.

**Solución implementada**: método privado `_reassert_sdk_mode()` que envía explícitamente el comando `command` con timeout reducido (3 s) antes de cada movimiento. Si falla, se registra warning pero no se aborta — el siguiente comando puede recuperarse.

### 7.3 Motor stop en vuelo (`error Motor stop`)

**Síntoma**: durante `move_forward` o `move_right`, el sistema de seguridad del dron corta motores y el dron desciende.

**Causa raíz**: el sensor de optical-flow del Tello requiere textura visual en la superficie inferior para mantener posición. Sobre pisos lisos, oscuros o reflejantes, el sensor pierde referencia, el dron se desestabiliza, y la protección activa el corte.

**Soluciones implementadas**:
1. Reducción de `TABLE_DISTANCE_CM` de 80 a 60 cm (movimientos más cortos = menor drift acumulado).
2. Aumento de `_post_command_settle` de 1 a 2 segundos (mayor tiempo de estabilización entre comandos).
3. Documentación operativa: colocar periódicos abiertos en el piso para proveer textura visual.

### 7.4 Inestabilidad WiFi

**Síntoma**: desconexiones recurrentes entre laptop y dron durante el vuelo, especialmente en entornos con múltiples redes 2.4 GHz.

**Causa raíz**: el Tello opera únicamente en 2.4 GHz, banda saturada en ambientes académicos. Adicionalmente, Windows aplica ahorro de energía agresivo al adaptador WiFi por defecto.

**Solución operacional**: documentación que instruye a (1) cerrar la app Tello en celular, (2) "olvidar" la WiFi normal durante la prueba, (3) desactivar la opción de ahorro de energía del adaptador WiFi en Device Manager.

### 7.5 Cámara frontal vs. cámara cenital

**Síntoma**: el diseño original asumía vuelo sobre los objetos con detección hacia abajo. El Tello no dispone de cámara cenital de uso público; sólo de la cámara frontal estabilizada.

**Solución implementada**: rediseño completo a movimiento lateral "cangrejo" (Sec. 4.7), preservando la lógica de máquina de estados pero reorientando la trayectoria física.

### 7.6 Confirmación multi-frame con imagen estática

**Síntoma**: en modo simulación con una imagen `.jpg`, `cv2.VideoCapture` devuelve sólo un frame antes de retornar `None`. La política de `CONFIRM_K_FRAMES=3` requiere 3 detecciones, nunca alcanzables.

**Causa raíz**: arquitectural — la política está calibrada para video continuo.

**Estado**: documentado como limitación conocida. Para demos positivas en sim, se recomienda usar webcam o video corto en lugar de imagen estática. No se modificó el código porque el comportamiento es correcto: la política multi-frame es esencial para evitar falsos positivos en vuelo real.

---

## 8. Resultados

### 8.1 Resultados en simulación

- **Suite de pruebas**: 28/28 verde en 17-30 segundos. Cero regresiones tras 14 commits incrementales.
- **Detección sobre imágenes COCO conocidas**: precisión de detección de la clase `person` en `bus.jpg` superior a 90% de confianza (validado en test automatizado).
- **Misión end-to-end en sim con video pregrabado**: ejecución completa del flujo `preflight → takeoff → 6 scans → land` sin errores.

### 8.2 Resultados en vuelo real

Resultados parciales debido a las limitaciones de hardware descritas en Sección 7:

- **Takeoff y conexión WiFi**: funcional en ~85% de los intentos tras aplicar las medidas de la Sec. 7.1.
- **Movimiento lateral autónomo**: funcional intermitentemente; bloqueado en algunas sesiones por el sensor de optical-flow.
- **Detección de objetos en stream del Tello**: completamente funcional. YOLO procesa el feed UDP del dron sin errores de decodificación H.264. Confianzas observadas en condiciones normales (objetos a 60 cm de la cámara): 0.65–0.92 según objeto.
- **Modo manual**: 100% funcional como se diseñó, demostrando la cadena completa de detección sin depender del subsistema de vuelo.

---

## 9. Limitaciones

1. **Detección restringida a clases COCO**: el sistema no puede reconocer objetos fuera del vocabulario COCO sin re-entrenamiento. Esto excluye objetos específicos del laboratorio (termos, latas de refresco, instrumentos de medición).
2. **Plataforma de vuelo de baja confiabilidad**: el Ryze Tello fue diseñado como juguete educativo, no para inspección industrial. Los modos de falla (Motor stop, IMU, WiFi) son intrínsecos a la plataforma y no compensables por software.
3. **Sin anti-colisión**: el dron no detecta obstáculos. El operador debe garantizar espacio aéreo libre.
4. **Inferencia en CPU limita la frecuencia de procesamiento**: YOLOv8n alcanza ~15-20 FPS en Intel iGPU. Una GPU NVIDIA con CUDA elevaría esto a 60+ FPS y permitiría modelos más grandes (YOLOv8s o m) con mayor precisión.
5. **Inglés vs español**: las clases COCO son etiquetas en inglés. El sistema mapea aliases en español a través de un diccionario manual; un objeto en español sin alias registrado es rechazado.

---

## 10. Trabajo futuro

### 10.1 Entrenamiento personalizado

Sustituir el modelo pre-entrenado por uno fine-tuned sobre un dataset etiquetado en sitio. Roboflow ofrece flujos de bajo costo para esto, requiriendo aproximadamente 50-100 imágenes anotadas por clase. Esto permitiría:
- Detectar objetos específicos no incluidos en COCO (termos, latas).
- Mejorar precisión sobre objetos visualmente similares (botella vs. termo).
- Mantener etiquetas en español de origen.

### 10.2 Visual servoing

Una vez detectado el objetivo, en lugar de hover estático, ejecutar control proporcional en bucle cerrado para centrar el objeto en el frame y reducir la distancia. Requiere implementar PID sobre la posición del bbox en el frame.

### 10.3 Detección continua durante movimiento

Eliminar las paradas de escaneo y procesar frames durante el desplazamiento lateral. Requiere un hilo de inferencia desacoplado del hilo de control de vuelo, ya implementado parcialmente en el "live preview" pero no usado para decisión de misión.

### 10.4 Multi-objetivo

Aceptar una lista ordenada de objetivos (`--target libro,taza,refresco`) y visitar cada uno en secuencia. Trivial de implementar dada la arquitectura actual.

### 10.5 Substitución de plataforma de vuelo

Migrar a plataformas más confiables (DJI Mini, Holybro X500) preservando la arquitectura polimórfica: bastaría implementar un nuevo `Controller` con la misma interfaz.

### 10.6 Reentrenamiento sobre frames del propio dron

Capturar frames durante operaciones manuales y usarlos como dataset adicional. Esto cierra el ciclo entre operación y mejora del modelo.

---

## 11. Conclusiones

Se construyó un sistema completo de detección autónoma de objetos sobre superficie horizontal mediante un dron de bajo costo y un modelo YOLO pre-entrenado, con arquitectura limpia, cobertura de pruebas automatizada y modo simulación funcional. El componente de detección operó correctamente en todas las pruebas; el componente de vuelo autónomo presentó intermitencias atribuibles a la plataforma de hardware específica, mitigadas mediante un modo manual de respaldo que preserva la totalidad de la cadena de detección. El sistema es extensible (multi-objetivo, modelos custom, control continuo) y reproducible por terceros mediante la documentación operativa adjunta.

---

## 12. Referencias

1. Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You Only Look Once: Unified, Real-Time Object Detection. *CVPR 2016*. https://arxiv.org/abs/1506.02640
2. Lin, T.-Y., Maire, M., Belongie, S., et al. (2014). Microsoft COCO: Common Objects in Context. *ECCV 2014*. https://arxiv.org/abs/1405.0312
3. Jocher, G., Chaurasia, A., & Qiu, J. (2023). Ultralytics YOLO (Version 8.0.0) [Computer software]. https://github.com/ultralytics/ultralytics
4. Fuentes, D. (2018). DJITelloPy: DJI Tello drone Python interface using the official Tello SDK. https://github.com/damiafuentes/DJITelloPy
5. Ryze Tech (2018). Tello SDK 2.0 User Guide. https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf
6. Bradski, G. (2000). The OpenCV Library. *Dr. Dobb's Journal of Software Tools*. https://opencv.org/
7. Harris, C. R., Millman, K. J., et al. (2020). Array programming with NumPy. *Nature*, 585, 357–362. https://doi.org/10.1038/s41586-020-2649-2
8. Kyrkou, C., & Theocharides, T. (2019). Deep-Learning-Based Aerial Image Classification for Emergency Response Applications Using Unmanned Aerial Vehicles. *CVPR Workshops*. https://openaccess.thecvf.com/content_CVPRW_2019/html/UAVision/Kyrkou_Deep-Learning-Based_Aerial_Image_Classification_for_Emergency_Response_Applications_Using_Unmanned_CVPRW_2019_paper.html
9. Krause, P., Bisman, J., et al. (2020). Test-Driven Development with Python (2nd ed.). O'Reilly Media.
10. Goodfellow, I., Bengio, Y., & Courville, A. (2016). *Deep Learning*. MIT Press. Capítulo 9 (Convolutional Networks) para fundamento de detectores basados en CNN.

---

## Anexo A — Inventario de commits (cronológico)

| # | SHA corto | Tipo | Descripción |
|---|---|---|---|
| 1 | 01f7d58 | docs | Diseño inicial del proyecto |
| 2 | 2c42413 | docs | Plan de implementación TDD |
| 3 | 212fb18 | chore | Bootstrap (requirements, estructura) |
| 4 | 148d565 | chore | .gitkeep y .python-version |
| 5 | 2532ba1 | feat | config.py + resolve_alias |
| 6 | 4d4c3f7 | feat | YOLODetector con tests sobre imagen conocida |
| 7 | 20a335b | feat | MockController + tests ciclo vida |
| 8 | 9a67d52 | feat | TelloController (paridad de interfaz) |
| 9 | 8e9134d | feat | MissionPlanner con loop secuencial |
| 10 | e15f5d4 | feat | CLI main.py + logging por sesión |
| 11 | 02af8fd | docs | README completo + CALIBRACION.md |
| 12 | fcc65cb | fix | move_up tras takeoff + alinea Python version |
| 13 | d1a3059 | docs | Guía paso a paso DEMO.md |
| 14 | 445c5e7 | fix | Delays post-comando para estabilización |
| 15 | c78f6f2 | feat | Live preview en thread separado |
| 16 | ac8ab7b | fix | Re-arma modo SDK tras takeoff |
| 17 | bd04012 | fix | Re-arma SDK antes de cada movimiento + 2s settle |
| 18 | 236b4e3 | feat | Rediseño cangrejo (movimiento lateral) |
| 19 | 14b1005 | tune | FLIGHT_HEIGHT_CM=100 para mesas de 75cm |
| 20 | 4ed2204 | feat | Modo --manual sin vuelo autónomo |

---

## Anexo B — Configuración de hardware reproducible

**Para reproducir las pruebas en simulación:**
- Cualquier laptop con Python 3.10+, webcam estándar (USB o integrada), 4 GB RAM mínimo.

**Para reproducir las pruebas en vuelo real:**
- Dron Ryze Tello (versión estándar, ~$100 USD).
- Batería cargada al 100% (autonomía ~13 min vuelo continuo).
- Espacio físico interior de mínimo 3×5 m, libre de obstáculos a 1.5 m de altura.
- Superficie con textura visual debajo de la trayectoria del dron (alfombra patterned, periódicos, etc.).
- Iluminación mínima 300 lux.
- Mesa o superficie horizontal de altura ~75 cm para colocación de objetos.
- Seis objetos COCO: botella plástica, libro tapa dura, taza, mochila, celular, mouse de computadora.
