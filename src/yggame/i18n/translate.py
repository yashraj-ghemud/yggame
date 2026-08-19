# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Small runtime localization manager with locale fallback."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class TranslationManager:
    def __init__(self, *, default_locale: str = "en") -> None:
        self.default_locale = default_locale
        self.locale = default_locale
        self._catalogs: dict[str, dict[str, str]] = {}

    def register(self, locale: str, values: Mapping[str, str], *, replace: bool = False) -> None:
        if not locale:
            raise ValueError("locale cannot be empty")
        catalog = self._catalogs.setdefault(locale, {})
        if replace:
            catalog.clear()
        catalog.update(values)

    def set_locale(self, locale: str) -> None:
        self.locale = locale

    def translate(self, key: str, *, fallback: str | None = None, **values: Any) -> str:
        text = self._catalogs.get(self.locale, {}).get(key)
        if text is None and "-" in self.locale:
            text = self._catalogs.get(self.locale.split("-", 1)[0], {}).get(key)
        if text is None:
            text = self._catalogs.get(self.default_locale, {}).get(key)
        if text is None:
            text = fallback if fallback is not None else key
        return text.format(**values)

    __call__ = translate
