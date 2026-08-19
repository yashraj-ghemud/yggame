# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Typed-enough hierarchical configuration with atomic JSON persistence."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

from .errors import ConfigurationError


class Config:
    """Mutable mapping with dotted-path access and atomic saves."""

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self._values: dict[str, Any] = dict(values or {})

    def get(self, path: str, default: Any = None) -> Any:
        current: Any = self._values
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def require(self, path: str) -> Any:
        value = self.get(path, _MISSING)
        if value is _MISSING:
            raise ConfigurationError(f"missing required configuration value: {path}")
        return value

    def set(self, path: str, value: Any) -> None:
        parts = path.split(".")
        if any(not part for part in parts):
            raise ConfigurationError(f"invalid configuration path: {path!r}")
        current = self._values
        for part in parts[:-1]:
            child = current.get(part)
            if child is None:
                child = {}
                current[part] = child
            if not isinstance(child, dict):
                raise ConfigurationError(f"cannot descend through non-object value: {part}")
            current = child
        current[parts[-1]] = value

    def update(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value) if "." in key else self._values.__setitem__(key, value)

    def as_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(json.dumps(self._values)))

    def __contains__(self, path: str) -> bool:
        return self.get(path, _MISSING) is not _MISSING

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    @classmethod
    def load(
        cls, path: str | os.PathLike[str], *, defaults: dict[str, Any] | None = None
    ) -> Config:
        config = cls(defaults)
        file_path = Path(path)
        if not file_path.exists():
            return config
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"could not load configuration {file_path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigurationError("configuration root must be a JSON object")
        config._merge(config._values, raw)
        return config

    def save(self, path: str | os.PathLike[str]) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=file_path.parent,
                delete=False,
                prefix=f".{file_path.name}.",
            ) as temp:
                json.dump(self._values, temp, indent=2, sort_keys=True)
                temp.write("\n")
                temp_path = Path(temp.name)
            temp_path.replace(file_path)
        except (OSError, TypeError, ValueError) as exc:
            raise ConfigurationError(f"could not save configuration {file_path}: {exc}") from exc

    @staticmethod
    def _merge(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                Config._merge(target[key], value)
            else:
                target[key] = value


_MISSING = object()
