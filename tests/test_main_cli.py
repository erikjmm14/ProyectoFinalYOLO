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
