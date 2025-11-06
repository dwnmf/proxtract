"""Tests for proxtract.utils helpers."""

from __future__ import annotations

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
