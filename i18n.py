# -*- coding: utf-8 -*-
"""Small JSON-backed translation helper for UI copy."""

import json
from pathlib import Path
from typing import Any, Dict


_ROOT = Path(__file__).parent / "i18n"
_DEFAULT_LANGUAGE = "zh"
_current_language = _DEFAULT_LANGUAGE
_cache: Dict[str, Dict[str, Any]] = {}


def normalize_language(language: str | None) -> str:
    value = (language or _DEFAULT_LANGUAGE).strip().lower()
    return value if value in {"zh", "en"} else _DEFAULT_LANGUAGE


def set_language(language: str | None) -> None:
    global _current_language
    _current_language = normalize_language(language)


def get_language() -> str:
    return _current_language


def _load(language: str) -> Dict[str, Any]:
    language = normalize_language(language)
    if language in _cache:
        return _cache[language]
    path = _ROOT / f"{language}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    _cache[language] = data if isinstance(data, dict) else {}
    return _cache[language]


def t(msg_key: str, default: Any = None, **kwargs: Any) -> str:
    data = _load(_current_language)
    fallback = _load(_DEFAULT_LANGUAGE)
    text = data.get(msg_key, fallback.get(msg_key, default if default is not None else msg_key))
    if kwargs:
        try:
            return str(text).format(**kwargs)
        except Exception:
            return str(text)
    return str(text)
