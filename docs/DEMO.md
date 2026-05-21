# Guía paso a paso de la demostración

Esta guía es para alguien que **nunca ha volado el Tello**. Síguela en orden.

---

## Parte 1 — Un día antes

- [ ] **Cargar el Tello**: enchufar la batería al cargador USB. Se llena en ~1 hora. La luz pasa de roja a verde.
- [ ] **Cargar batería de respaldo** si tienes (cada vuelo gasta ~3-5%, pero da más confianza tener 2 baterías).
- [ ] **Cargar la laptop al 100%**.
- [ ] **Probar el código en sim** para confirmar que todo corre:
  ```powershell
  cd "c:\Users\erikj\OneDrive\Documents\UAQ\DCC\Optativa I\ProyectoFinalYOLO"
  .venv\Scripts\activate
  python main.py --mode sim --video 0 --target taza
  ```
  Pon una taza frente a la webcam. Debe terminar con "🎯 Objetivo 'cup' encontrado". Si no funciona en sim, no va a funcionar con el dron.
- [ ] **Tener listos los 6 objetos**: refresco/botella, libro, taza, mochila, celular, mouse.

---

## Parte 2 — Preparar el espacio

- [ ] **Necesitas ~6 metros de largo × 3 metros de ancho** despejados.
- [ ] **Apaga aire acondicionado y ventiladores** cercanos. Las corrientes de aire vuelan al Tello.
- [ ] **Coloca las 6 mesas en fila recta**, separadas **80 cm centro a centro**. Mide con cinta.
- [ ] **Pon 1 objeto al centro de cada mesa**. El orden es libre — el dron las recorre todas hasta encontrar el que buscas.
- [ ] **Marca con cinta el punto de despegue del dron**: debe estar **80 cm antes de la mesa 1** y centrado.
- [ ] **Asegúrate de que arriba del recorrido no haya lámparas, ventiladores de techo, ni cables**. El dron sube a **120 cm**.

```
    [Mesa 1]   [Mesa 2]   [Mesa 3]   [Mesa 4]   [Mesa 5]   [Mesa 6]
       |          |          |          |          |          |
       *----------*----------*----------*----------*----------*
       80cm       80cm       80cm       80cm       80cm
   
   [DRON]
     ^
   80cm antes de Mesa 1
```

---

## Parte 3 — Encender el dron

1. **Saca la batería del cargador** y métela al Tello (encaja con clic).
2. **Presiona el botón** del costado del Tello una vez. La luz parpadea **amarilla** primero, luego se vuelve **amarilla fija** o **verde**.
3. **Espera ~10 segundos** a que el Tello cree su propia red WiFi.

---

## Parte 4 — Conectar la laptop al Tello

1. Click en el icono de WiFi de Windows (esquina inferior derecha).
2. Busca una red llamada **`TELLO-XXXXXX`** (las X son números/letras).
3. Click → **Conectar**. **NO** pide contraseña.
4. Espera a que diga "Conectado, sin internet" — eso es **normal**. Pierdes acceso a internet mientras estés conectado al Tello.

⚠️ Si por error te reconectas a tu WiFi normal a mitad del vuelo, el dron se queda sin comandos y aterriza solo. Mantén el Tello conectado todo el vuelo.

---

## Parte 5 — Lanzar la misión

1. Abre **PowerShell** (Inicio → escribe "powershell").
2. Pega esto y presiona Enter (cambia `libro` por el objeto que quieras buscar):

```powershell
cd "c:\Users\erikj\OneDrive\Documents\UAQ\DCC\Optativa I\ProyectoFinalYOLO"
.venv\Scripts\activate
python main.py --mode real --target libro
```

3. Lee la salida. Debe aparecer en orden:
   - `Preflight checks...`
   - `[TELLO] connect`
   - `Batería: XX%` (debe ser ≥ 30%)
   - `[TELLO] takeoff` → **el dron despega y sube ~80 cm**
   - `[TELLO] move_up 40cm` → **sube a 120 cm total**
   - `--- Mesa 1/6 ---`
   - `[TELLO] move_forward 80cm` → **avanza a la primera mesa**
   - Hover ~2.5 s mientras escanea
   - Si no detecta → `--- Mesa 2/6 ---` y avanza
   - Cuando detecta → `🎯 Objetivo 'book' encontrado en mesa N`
   - Hover 4 s sobre el objeto
   - `[TELLO] land` → **aterriza solo**

---

## Parte 6 — Si algo sale mal (abort de emergencia)

**3 maneras de detener el dron**, de menos a más drástica:

1. **Tecla `Q`** en la ventana OpenCV (la que muestra el video con bounding boxes). El dron aterriza ordenadamente.
2. **Ctrl + C** en la terminal de PowerShell. Mismo efecto.
3. **Apagar el Tello desde su botón** (último recurso — corta motores en el aire, cae).

Si el dron se vuelve loco (va contra una pared, gira incontrolablemente), opción 3 sin pensarlo. Mejor un Tello caído de 1 metro que un Tello que choca con alguien.

---

## Parte 7 — Grabar el video

Tienes 3 opciones. La mejor es combinar A + B.

### Opción A: celular + un compañero (esencial)

- Pídele a alguien que grabe con su celular desde un **costado**, paralelo a las mesas.
- Que capture: el dron despegando, avanzando, deteniéndose sobre la mesa correcta, y aterrizando.
- Resolución mínima 1080p para que se vean los objetos.

### Opción B: grabar la pantalla de la laptop (recomendado)

Windows trae grabador integrado:

1. Antes de correr `python main.py`, presiona **`Win + G`** → se abre la Xbox Game Bar.
2. Click en el ícono de grabar (●) o presiona **`Win + Alt + R`**.
3. Corre tu comando. Todo lo que aparezca en pantalla se graba: los logs del mission.py y la ventana OpenCV con las bounding boxes.
4. Cuando termine la misión, presiona **`Win + Alt + R`** otra vez para parar.
5. El video queda en `Videos\Capturas`.

### Opción C: las dos juntas

Mejor demo: video del dron volando (opción A) + video de los logs y bounding boxes (opción B). Las editas juntas con cualquier editor (CapCut, ClipChamp, etc.) — split screen o cortes alternados.

### Lo que debe quedar grabado para que se vea el funcionamiento

- ✅ Comando que tecleas (qué objeto buscas)
- ✅ Despegue del dron
- ✅ El dron recorriendo las mesas
- ✅ El dron deteniéndose sobre la mesa correcta (el objeto del comando)
- ✅ Log "🎯 Objetivo encontrado en mesa N"
- ✅ Aterrizaje

---

## Parte 8 — Checklist antes de CADA intento

Si vas a hacer varios intentos (recomendado), revisa esto cada vez:

- [ ] Batería del Tello ≥ 50% (en el log dice el %)
- [ ] Laptop sigue conectada a `TELLO-XXXXXX`
- [ ] Dron alineado con mesa 1 (~80 cm antes, centrado)
- [ ] Mesas en su lugar, objetos visibles desde arriba
- [ ] Espacio aéreo despejado a 120 cm
- [ ] Nadie debajo del dron ni en su trayectoria
- [ ] Cámara del compañero lista
- [ ] Grabación de pantalla activada

---

## Parte 9 — Plan recomendado de grabación (orden sugerido)

Para que el video se vea profesional:

1. **Intento de prueba sin grabar**: vuela una vez para confirmar que todo funciona. Si hay drift en el avance, ajusta `TABLE_DISTANCE_CM` en `config.py`.
2. **Demo 1 — Objeto en mesa cercana** (mesa 2, por ejemplo): rápido y visual. Buscas `--target taza`.
3. **Demo 2 — Objeto en mesa lejana** (mesa 5 o 6): muestra que recorre varias antes de encontrar.
4. **Demo 3 — Cambiando el target**: corres con `--target libro` y el dron va a la mesa con el libro, sin importar donde esté.
5. **Demo 4 (opcional) — Objeto inexistente**: pon solo 5 objetos físicamente, busca el faltante. El dron recorre las 6 mesas y aterriza sin encontrar — demuestra que el código maneja ese caso.

---

## Parte 10 — Problemas comunes y soluciones

| Problema | Causa probable | Solución |
|---|---|---|
| `Batería insuficiente: XX% < mínimo 30%` antes de despegar | Tello descargado | Cargar la batería |
| `[TELLO] connect` falla / cuelga | Laptop no conectada a TELLO-XXXX | Verificar WiFi de Windows |
| El dron despega pero no avanza | Drift / clamp de djitellopy (min 20 cm) | Verificar que `TABLE_DISTANCE_CM ≥ 20` en config.py |
| No detecta ningún objeto | Altura muy alta o umbral muy estricto | Bajar `FLIGHT_HEIGHT_CM` a 90 o `CONF_THRESHOLD` a 0.40 |
| Confunde mesas vecinas | Detecciones cruzadas entre mesas adyacentes | Subir `CONFIRM_K_FRAMES` a 5 o subir `CONF_THRESHOLD` a 0.65 |
| El dron deriva al avanzar (no va recto) | Calibración de motores o corriente de aire | Pre-flight: presiona el botón del Tello 5s para auto-calibrar; cierra ventanas |
| Se desconecta a mitad del vuelo | WiFi débil o interferencia con otras redes | Probar en lugar con menos redes 2.4 GHz; el código aterriza solo si pasa esto |
| Pantalla se queda congelada | La ventana OpenCV bloqueó | Presiona `Q` con la ventana enfocada, o Ctrl+C en terminal |

---

## Parte 11 — Después de la demo

- [ ] **Saca la batería del Tello** (no la dejes adentro descargándose).
- [ ] **Recoge los objetos** y las mesas.
- [ ] **Reconecta la laptop a tu WiFi normal** para recuperar internet.
- [ ] **Edita el video** si grabaste por separado.

---

## Resumen ultra-corto (la "chuleta")

1. Mesas en fila, 80 cm de separación.
2. Dron 80 cm antes de mesa 1, centrado.
3. Enciende Tello → laptop a WiFi `TELLO-XXXXX`.
4. PowerShell:
   ```powershell
   cd "c:\Users\erikj\OneDrive\Documents\UAQ\DCC\Optativa I\ProyectoFinalYOLO"
   .venv\Scripts\activate
   python main.py --mode real --target libro
   ```
5. **`Q`** = aterrizaje seguro. **Apagar Tello** = corte de motores (emergencia).
6. Graba: compañero con celular + `Win + Alt + R` para pantalla.
