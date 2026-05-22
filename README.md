# Proyecto Final YOLO — Búsqueda con dron Tello

Sistema que vuela un dron Ryze Tello sobre 6 mesas, detecta objetos con YOLOv8 (COCO) y se detiene sobre la mesa donde está el objeto objetivo.

## Cómo funciona (resumen)

1. Pones 6 objetos sobre 6 mesas en fila recta: refresco, libro, taza, mochila, celular, mouse.
2. Corres `python main.py --mode real --target libro` (por ejemplo).
3. El dron despega, avanza sobre cada mesa, escanea con YOLO, y se detiene sobre la mesa donde está el libro.

## Requisitos

- Python 3.10, 3.11 o 3.12
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
## Contribuidores
Carlos Eugenio Miranda Rocha
Guillermo Carlos Guerrero Camargo