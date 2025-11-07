"""Tests for proxtract.utils helpers."""

from __future__ import annotations

import io

from proxtract import utils
from proxtract.utils import normalize_bool


def test_normalize_bool_from_strings():
    assert normalize_bool("true", False) is True
    assert normalize_bool("FALSE", True) is False
    assert normalize_bool("no", True) is False
    assert normalize_bool("1", False) is True
    assert normalize_bool("0", True) is False


def test_normalize_bool_from_numbers_and_defaults():
    assert normalize_bool(1, False) is True
    assert normalize_bool(0, True) is False
    assert normalize_bool(3, False) is True
    assert normalize_bool(-1, False) is True
    assert normalize_bool(object(), True) is True


def test_supports_color_env_overrides(monkeypatch):
    class DummyStream(io.StringIO):
        def isatty(self) -> bool:  # type: ignore[override]
            return True

    stream = DummyStream()
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("PYCHARM_HOSTED", raising=False)
    monkeypatch.delenv("PROXTRACT_NO_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("PROXTRACT_FORCE_COLOR", raising=False)

    assert utils.supports_color(stream) is True

    monkeypatch.setenv("PYCHARM_HOSTED", "1")
    assert utils.supports_color(stream) is False

    monkeypatch.setenv("PROXTRACT_FORCE_COLOR", "1")
    assert utils.supports_color(stream) is True


def test_create_console_respects_support_detection(monkeypatch):
    monkeypatch.setattr(utils, "supports_color", lambda stream=None: False)
    console = utils.create_console()
    assert console.no_color is True

    monkeypatch.setattr(utils, "supports_color", lambda stream=None: True)
    console_colored = utils.create_console()
    assert console_colored.no_color is False
