# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Safe serialization helpers for save files, replays, and network snapshots.

The codec deliberately produces JSON-compatible values and rejects opaque runtime
objects. Game code can register explicit codecs for domain types instead of relying
on fragile pickle behavior.
"""

from __future__ import annotations

import dataclasses
import enum
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from .errors import SerializationError
from .geometry import Rect, Vec2

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class TypeTag:
    name: str
    version: int = 1


class CodecRegistry:
    """Registry of explicit encoders and decoders keyed by stable type names."""

    def __init__(self) -> None:
        self._encoders: dict[type[Any], tuple[TypeTag, Any]] = {}
        self._decoders: dict[str, tuple[type[Any], Any]] = {}

    def register(
        self, type_: type[T], name: str, encoder: Any, decoder: Any, *, version: int = 1
    ) -> None:
        if not name or version < 1:
            raise ValueError("codec names must be non-empty and versions positive")
        if type_ in self._encoders or name in self._decoders:
            raise ValueError(f"duplicate codec registration: {name}")
        tag = TypeTag(name, version)
        self._encoders[type_] = (tag, encoder)
        self._decoders[name] = (type_, decoder)

    def encode(self, value: Any) -> Any:
        return _encode(value, self)

    def decode(self, value: Any, expected: type[T] | None = None) -> T | Any:
        decoded = _decode(value, self)
        if expected is not None and not isinstance(decoded, expected):
            raise SerializationError(
                f"decoded value has type {type(decoded).__name__}, expected {expected.__name__}"
            )
        return decoded

    def _custom_encoder(self, type_: type[Any]) -> tuple[TypeTag, Any] | None:
        return self._encoders.get(type_)

    def _custom_decoder(self, name: str) -> tuple[type[Any], Any] | None:
        return self._decoders.get(name)


def _encode(value: Any, registry: CodecRegistry) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    custom = registry._custom_encoder(type(value))
    if custom:
        tag, encoder = custom
        return {
            "__type__": tag.name,
            "__version__": tag.version,
            "value": _encode(encoder(value), registry),
        }
    if isinstance(value, enum.Enum):
        return {
            "__enum__": f"{type(value).__module__}:{type(value).__qualname__}",
            "value": _encode(value.value, registry),
        }
    if isinstance(value, Vec2):
        return {"__type__": "yggame.geometry.Vec2", "x": value.x, "y": value.y}
    if isinstance(value, Rect):
        return {
            "__type__": "yggame.geometry.Rect",
            "x": value.x,
            "y": value.y,
            "width": value.width,
            "height": value.height,
        }
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            "__dataclass__": f"{type(value).__module__}:{type(value).__qualname__}",
            "fields": {
                field.name: _encode(getattr(value, field.name), registry)
                for field in dataclasses.fields(value)
            },
        }
    if isinstance(value, Mapping):
        return {str(key): _encode(item, registry) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(item, registry) for item in value]
    if isinstance(value, (set, frozenset)):
        return {"__set__": [_encode(item, registry) for item in value]}
    raise SerializationError(f"unsupported value for serialization: {type(value).__name__}")


def _decode(value: Any, registry: CodecRegistry) -> Any:
    if isinstance(value, list):
        return [_decode(item, registry) for item in value]
    if not isinstance(value, dict):
        return value
    if "__type__" in value:
        name = value["__type__"]
        if name == "yggame.geometry.Vec2":
            return Vec2(float(value["x"]), float(value["y"]))
        if name == "yggame.geometry.Rect":
            return Rect(
                float(value["x"]), float(value["y"]), float(value["width"]), float(value["height"])
            )
        custom = registry._custom_decoder(name)
        if custom is None:
            raise SerializationError(f"unknown serialized type: {name}")
        _, decoder = custom
        return decoder(_decode(value.get("value"), registry))
    if "__set__" in value:
        return set(_decode(item, registry) for item in value["__set__"])
    if "__enum__" in value:
        module_name, _, qualname = value["__enum__"].partition(":")
        if not module_name or not qualname:
            raise SerializationError(f"invalid enum tag: {value['__enum__']!r}")
        raise SerializationError(
            f"enum {module_name}:{qualname} needs an explicit codec before decoding"
        )
    if "__dataclass__" in value:
        raise SerializationError(
            f"dataclass {value['__dataclass__']} needs an explicit codec before decoding"
        )
    return {key: _decode(item, registry) for key, item in value.items()}


def dumps(value: Any, registry: CodecRegistry | None = None, **kwargs: Any) -> str:
    """Encode a value and dump it to JSON with deterministic key ordering."""
    codec = registry or CodecRegistry()
    try:
        return json.dumps(codec.encode(value), sort_keys=True, **kwargs)
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"could not encode JSON: {exc}") from exc


def loads(text: str, registry: CodecRegistry | None = None) -> Any:
    codec = registry or CodecRegistry()
    try:
        return codec.decode(json.loads(text))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise SerializationError(f"could not decode JSON: {exc}") from exc


def dump_file(path: str | Path, value: Any, registry: CodecRegistry | None = None) -> None:
    Path(path).write_text(dumps(value, registry, indent=2) + "\n", encoding="utf-8")


def load_file(path: str | Path, registry: CodecRegistry | None = None) -> Any:
    return loads(Path(path).read_text(encoding="utf-8"), registry)
