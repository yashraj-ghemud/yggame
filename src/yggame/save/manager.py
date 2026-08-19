# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Versioned save-game persistence with migration support."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from yggame.core.errors import SerializationError

Migration = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class SaveEnvelope:
    schema: int
    game_version: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "game_version": self.game_version, "payload": self.payload}


class SaveManager:
    def __init__(
        self, *, schema: int, game_version: str, migrations: dict[int, Migration] | None = None
    ) -> None:
        if schema < 1:
            raise ValueError("schema must be at least 1")
        self.schema = schema
        self.game_version = game_version
        self.migrations = migrations or {}

    def save(self, path: str | Path, payload: dict[str, Any]) -> None:
        envelope = SaveEnvelope(self.schema, self.game_version, payload)
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                delete=False,
            ) as temp:
                json.dump(envelope.as_dict(), temp, indent=2, sort_keys=True)
                temp.write("\n")
                temporary = Path(temp.name)
            temporary.replace(destination)
        except (OSError, TypeError, ValueError) as exc:
            raise SerializationError(f"could not save {destination}: {exc}") from exc

    def load(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SerializationError(f"could not load {source}: {exc}") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("payload"), dict):
            raise SerializationError("save file must contain an object payload")
        version = raw.get("schema")
        if not isinstance(version, int) or version < 1 or version > self.schema:
            raise SerializationError(f"unsupported save schema: {version!r}")
        return self.migrate_payload(dict(raw["payload"]), version)

    def migrate_payload(self, payload: dict[str, Any], version: int) -> dict[str, Any]:
        if version < 1 or version > self.schema:
            raise SerializationError(f"unsupported save schema: {version}")
        result = dict(payload)
        while version < self.schema:
            migration = self.migrations.get(version)
            if migration is None:
                raise SerializationError(f"no migration registered from schema {version}")
            result = migration(result)
            version += 1
        return result


class Autosave:
    def __init__(self, manager: SaveManager, path: str | Path, interval: float = 60.0) -> None:
        if interval <= 0:
            raise ValueError("autosave interval must be positive")
        self.manager, self.path, self.interval = manager, Path(path), interval
        self.elapsed = 0.0

    def update(self, delta: float, payload_factory: Callable[[], dict[str, Any]]) -> bool:
        self.elapsed += max(0.0, delta)
        if self.elapsed < self.interval:
            return False
        self.elapsed %= self.interval
        self.manager.save(self.path, payload_factory())
        return True
