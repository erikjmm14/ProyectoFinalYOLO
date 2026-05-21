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
