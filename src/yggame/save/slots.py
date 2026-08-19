# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Production-oriented save-slot management built on SaveManager."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .manager import SaveManager


@dataclass(frozen=True, slots=True)
class SaveMetadata:
    slot: str
    created_at: str
    updated_at: str
    play_time: float = 0.0
    thumbnail: str | None = None
    label: str = ""


@dataclass(frozen=True, slots=True)
class SaveRecord:
    metadata: SaveMetadata
    checksum: str
    path: Path


class SaveSlots:
    """Manages multiple save slots without exposing raw file naming to game code."""

    def __init__(self, directory: str | Path, manager: SaveManager, *, backups: int = 3) -> None:
        if backups < 0:
            raise ValueError("backup count cannot be negative")
        self.directory = Path(directory)
        self.manager = manager
        self.backups = backups
        self.directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, slot: str) -> Path:
        self._validate_slot(slot)
        return self.directory / f"slot-{slot}.json"

    def save(
        self,
        slot: str,
        payload: dict[str, Any],
        *,
        play_time: float = 0.0,
        label: str = "",
        thumbnail: str | None = None,
    ) -> SaveRecord:
        destination = self.path_for(slot)
        if destination.exists() and self.backups:
            self._rotate_backups(destination)
        now = datetime.now(timezone.utc).isoformat()
        previous = self.inspect(slot)
        metadata = SaveMetadata(
            slot,
            previous.metadata.created_at if previous else now,
            now,
            max(0.0, play_time),
            thumbnail,
            label,
        )
        envelope = {"metadata": asdict(metadata), "payload": payload}
        encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        checksum = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        document = {"checksum": checksum, **envelope}
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.directory, prefix=f".{destination.name}.", delete=False
        ) as temp:
            json.dump(document, temp, indent=2, sort_keys=True)
            temp.write("\n")
            temporary = Path(temp.name)
        temporary.replace(destination)
        return SaveRecord(metadata, checksum, destination)

    def load(self, slot: str) -> dict[str, Any]:
        record = self.inspect(slot)
        if record is None:
            raise FileNotFoundError(f"save slot does not exist: {slot}")
        raw = json.loads(record.path.read_text(encoding="utf-8"))
        return self.manager.migrate_payload(
            raw["payload"], int(raw.get("schema", self.manager.schema))
        )

    def inspect(self, slot: str) -> SaveRecord | None:
        path = self.path_for(slot)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        metadata = SaveMetadata(**raw["metadata"])
        payload = raw["payload"]
        canonical = json.dumps(
            {"metadata": raw["metadata"], "payload": payload}, sort_keys=True, separators=(",", ":")
        )
        checksum = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if checksum != raw.get("checksum"):
            raise ValueError(f"save checksum mismatch: {slot}")
        return SaveRecord(metadata, checksum, path)

    def list(self) -> tuple[SaveRecord, ...]:
        records: list[SaveRecord] = []
        for path in sorted(self.directory.glob("slot-*.json")):
            slot = path.stem.removeprefix("slot-")
            record = self.inspect(slot)
            if record:
                records.append(record)
        return tuple(records)

    def delete(self, slot: str) -> None:
        path = self.path_for(slot)
        path.unlink(missing_ok=True)
        for backup in self.directory.glob(f".{path.name}.bak.*"):
            backup.unlink(missing_ok=True)

    def recover_latest_backup(self, slot: str) -> SaveRecord | None:
        path = self.path_for(slot)
        backups = sorted(self.directory.glob(f".{path.name}.bak.*"), reverse=True)
        if not backups:
            return None
        shutil.copy2(backups[0], path)
        return self.inspect(slot)

    def _rotate_backups(self, destination: Path) -> None:
        existing = sorted(self.directory.glob(f".{destination.name}.bak.*"), reverse=True)
        for index, backup in enumerate(existing, 1):
            if index >= self.backups:
                backup.unlink(missing_ok=True)
            else:
                backup.rename(self.directory / f".{destination.name}.bak.{index + 1}")
        shutil.copy2(destination, self.directory / f".{destination.name}.bak.1")

    @staticmethod
    def _validate_slot(slot: str) -> None:
        if not slot or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for character in slot
        ):
            raise ValueError(
                "save slot names may contain only letters, digits, underscores, and hyphens"
            )
