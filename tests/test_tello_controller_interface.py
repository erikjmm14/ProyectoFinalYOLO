"""Verifica que TelloController y MockController exponen los mismos métodos.

NO vuela el dron — solo inspecciona las clases.
"""
import inspect
from drone.mock_controller import MockController
from drone.tello_controller import TelloController


REQUIRED_METHODS = ["connect", "takeoff", "land", "move_forward",
                    "move_up", "move_right", "move_left", "send_rc_control",
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
