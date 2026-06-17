# -*- coding: utf-8 -*-
"""Runtime path helpers for source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    """Directory containing bundled read-only assets."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def runtime_root() -> Path:
    """Directory for mutable runtime files next to the executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def runtime_path(*parts: str) -> Path:
    return runtime_root().joinpath(*parts)
