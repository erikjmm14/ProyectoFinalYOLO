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
