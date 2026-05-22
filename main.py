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
    p.add_argument("--target", default=None,
                   help="Objeto a buscar (refresco, libro, taza, mochila, celular, mouse). "
                        "Requerido en modos default/manual. En --keyboard es opcional "
                        "(omítelo para detectar TODAS las clases COCO).")
    p.add_argument("--video", default="0",
                   help="Solo en sim: '0' webcam o ruta a video/imagen. Ignorado en real.")
    p.add_argument("--tables", type=int, default=config.DEFAULT_NUM_TABLES,
                   help="Numero de objetos a recorrer (default 6)")
    p.add_argument("--direction", choices=["right", "left", "forward"], default="right",
                   help="Direccion del recorrido entre objetos (default 'right', estilo cangrejo)")
    p.add_argument("--show", dest="show", action="store_true", default=True,
                   help="Mostrar ventana OpenCV (default activado)")
    p.add_argument("--no-show", dest="show", action="store_false",
                   help="Desactivar ventana OpenCV")
    p.add_argument("--manual", action="store_true", default=False,
                   help="Modo manual: solo conecta al dron y muestra YOLO, NO despega ni vuela. "
                        "Útil cuando el vuelo autónomo falla por IMU/motores. "
                        "El usuario carga el dron físicamente.")
    p.add_argument("--keyboard", action="store_true", default=False,
                   help="Modo teclado: control en vivo del dron con flechas + WASD, "
                        "YOLO detecta TODAS las clases COCO en pantalla. "
                        "Si no se pasa --target, se muestra detección sin objetivo específico.")
    p.add_argument("--speed", type=int, default=40,
                   help="Velocidad inicial en modo teclado (10-100, default 40).")
    return p


def build_components(args: argparse.Namespace):
    # En modo teclado, target es opcional. En los demás, requerido.
    if args.target is None:
        if not args.keyboard:
            raise ValueError(
                "--target es requerido (excepto en --keyboard). "
                "Usa --target refresco|libro|taza|mochila|celular|mouse"
            )
        target_coco = None
    else:
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
        log.error(f"Error de configuracion: {e}")
        return 2

    mission = MissionPlanner(
        controller=controller,
        detector=detector,
        num_tables=args.tables,
        direction=args.direction,
        show=args.show,
    )

    try:
        if args.keyboard:
            mission.run_keyboard(speed=args.speed)
            return 0
        if args.manual:
            found = mission.run_manual()
        else:
            found = mission.run()
    except KeyboardInterrupt:
        log.warning("Abort manual")
        return 130
    except Exception as e:
        log.exception(f"Falla en la mision: {e}")
        return 1

    return 0 if found else 3


if __name__ == "__main__":
    sys.exit(main())
