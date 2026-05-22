"""Constantes y aliases del proyecto."""

# ----- Vuelo -----
FLIGHT_HEIGHT_CM = 100        # Altura final tras takeoff+ascenso. Para mesa de 75cm.
TABLE_DISTANCE_CM = 60        # Distancia lateral entre objetos consecutivos (estilo cangrejo).
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
