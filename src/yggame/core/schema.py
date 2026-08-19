# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Small schema validation layer for configuration and content documents."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .errors import ConfigurationError

Validator = Callable[[Any], None]


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    expected: type[Any] | tuple[type[Any], ...] | None = None
    required: bool = False
    default: Any = None
    validator: Validator | None = None

    def validate(self, value: Any, path: str) -> Any:
        if self.expected and not isinstance(value, self.expected):
            expected = self.expected if isinstance(self.expected, tuple) else (self.expected,)
            names = ", ".join(item.__name__ for item in expected)
            raise ConfigurationError(f"{path} must be {names}, got {type(value).__name__}")
        if self.validator:
            try:
                self.validator(value)
            except Exception as exc:
                raise ConfigurationError(f"invalid value for {path}: {exc}") from exc
        return value


class Schema:
    def __init__(self, name: str, fields: Sequence[Field], *, allow_extra: bool = False) -> None:
        if not name:
            raise ValueError("schema name cannot be empty")
        self.name = name
        self.fields = {field.name: field for field in fields}
        self.allow_extra = allow_extra

    def validate(self, value: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise ConfigurationError(f"{self.name} must be an object")
        if not self.allow_extra:
            unknown = set(value) - set(self.fields)
            if unknown:
                raise ConfigurationError(f"{self.name} contains unknown fields: {sorted(unknown)}")
        result: dict[str, Any] = {}
        for name, field in self.fields.items():
            if name not in value:
                if field.required:
                    raise ConfigurationError(f"{self.name}.{name} is required")
                result[name] = field.default
                continue
            result[name] = field.validate(value[name], f"{self.name}.{name}")
        if self.allow_extra:
            result.update({key: item for key, item in value.items() if key not in self.fields})
        return result

    def defaults(self) -> dict[str, Any]:
        return {name: field.default for name, field in self.fields.items() if not field.required}


def one_of(*allowed: Any) -> Validator:
    def validate(value: Any) -> None:
        if value not in allowed:
            raise ValueError(f"expected one of {allowed!r}")

    return validate


def range_(minimum: float | None = None, maximum: float | None = None) -> Validator:
    def validate(value: Any) -> None:
        if minimum is not None and value < minimum:
            raise ValueError(f"must be at least {minimum}")
        if maximum is not None and value > maximum:
            raise ValueError(f"must be at most {maximum}")

    return validate


def sequence_of(expected: type[Any]) -> Validator:
    def validate(value: Any) -> None:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ValueError("must be a sequence")
        if any(not isinstance(item, expected) for item in value):
            raise ValueError(f"every item must be {expected.__name__}")

    return validate
