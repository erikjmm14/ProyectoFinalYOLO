import pytest
from config import resolve_alias, TARGET_ALIASES


def test_resolve_alias_known_spanish():
    assert resolve_alias("refresco") == "bottle"
    assert resolve_alias("libro") == "book"
    assert resolve_alias("taza") == "cup"
    assert resolve_alias("mochila") == "backpack"
    assert resolve_alias("celular") == "cell phone"
    assert resolve_alias("mouse") == "mouse"


def test_resolve_alias_case_insensitive():
    assert resolve_alias("REFRESCO") == "bottle"
    assert resolve_alias("Libro") == "book"


def test_resolve_alias_accepts_coco_class_directly():
    assert resolve_alias("bottle") == "bottle"
    assert resolve_alias("cell phone") == "cell phone"


def test_resolve_alias_unknown_raises():
    with pytest.raises(ValueError, match="termo"):
        resolve_alias("termo")


def test_target_aliases_has_six_objects():
    coco_classes = set(TARGET_ALIASES.values())
    assert coco_classes == {"bottle", "book", "cup", "backpack", "cell phone", "mouse"}
