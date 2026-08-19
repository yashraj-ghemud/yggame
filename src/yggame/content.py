# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Project content loading and validation primitives.

Content is represented as JSON-like documents with explicit kind/version fields.
Game projects can register schemas and loaders without coupling the pipeline to a
particular editor or filesystem layout.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core.errors import AssetError
from .core.schema import Schema


@dataclass(frozen=True, slots=True)
class ContentDocument:
    kind: str
    id: str
    version: int
    data: dict[str, Any]
    source: str = ""

    def __post_init__(self) -> None:
        if not self.kind or not self.id or self.version < 1:
            raise ValueError("content documents require kind, id, and positive version")


@dataclass(frozen=True, slots=True)
class ContentIssue:
    source: str
    path: str
    message: str
    severity: str = "error"


@dataclass(slots=True)
class ContentReport:
    issues: list[ContentIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def add(self, source: str, path: str, message: str, *, severity: str = "error") -> None:
        self.issues.append(ContentIssue(source, path, message, severity))

    def raise_if_invalid(self) -> None:
        if not self.valid:
            message = "; ".join(
                f"{issue.source}:{issue.path}: {issue.message}" for issue in self.issues
            )
            raise AssetError(message)


Loader = Callable[[ContentDocument], Any]


@dataclass(slots=True)
class ContentType:
    kind: str
    schema: Schema | None = None
    loader: Loader | None = None
    migrations: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = field(default_factory=dict)

    def migrate(self, version: int, data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        result = dict(data)
        while version < 1 + len(self.migrations):
            migration = self.migrations.get(version)
            if migration is None:
                break
            result = migration(result)
            version += 1
        return version, result


class ContentRegistry:
    def __init__(self) -> None:
        self.types: dict[str, ContentType] = {}
        self.documents: dict[tuple[str, str], ContentDocument] = {}

    def register(self, content_type: ContentType) -> None:
        if content_type.kind in self.types:
            raise ValueError(f"duplicate content kind: {content_type.kind}")
        self.types[content_type.kind] = content_type

    def add(self, document: ContentDocument, *, report: ContentReport | None = None) -> Any:
        content_type = self.types.get(document.kind)
        if content_type is None:
            if report:
                report.add(document.source, "kind", f"unknown content kind: {document.kind}")
            return None
        version, data = content_type.migrate(document.version, document.data)
        if content_type.schema:
            try:
                data = content_type.schema.validate(data)
            except Exception as exc:
                if report:
                    report.add(document.source, document.kind, str(exc))
                return None
        normalized = ContentDocument(document.kind, document.id, version, data, document.source)
        self.documents[(document.kind, document.id)] = normalized
        return content_type.loader(normalized) if content_type.loader else normalized

    def get(self, kind: str, content_id: str) -> ContentDocument:
        try:
            return self.documents[(kind, content_id)]
        except KeyError as exc:
            raise KeyError(f"unknown content document: {kind}/{content_id}") from exc

    def load_file(self, path: str | Path, *, report: ContentReport | None = None) -> Any:
        source = Path(path)
        report = report or ContentReport()
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report.add(str(source), "$", str(exc))
            return None
        if not isinstance(raw, dict):
            report.add(str(source), "$", "content root must be an object")
            return None
        missing = [key for key in ("kind", "id", "version", "data") if key not in raw]
        if missing:
            report.add(str(source), "$", f"missing required keys: {missing}")
            return None
        try:
            document = ContentDocument(
                str(raw["kind"]),
                str(raw["id"]),
                int(raw["version"]),
                dict(raw["data"]),
                str(source),
            )
        except (TypeError, ValueError) as exc:
            report.add(str(source), "$", str(exc))
            return None
        return self.add(document, report=report)

    def load_directory(
        self, directory: str | Path, *, report: ContentReport | None = None
    ) -> tuple[Any, ...]:
        report = report or ContentReport()
        loaded: list[Any] = []
        for path in sorted(Path(directory).rglob("*.json")):
            value = self.load_file(path, report=report)
            if value is not None:
                loaded.append(value)
        return tuple(loaded)


@dataclass(frozen=True, slots=True)
class BuildArtifact:
    source: str
    output: str
    kind: str
    checksum: str


class BuildManifest:
    def __init__(self) -> None:
        self.artifacts: list[BuildArtifact] = []

    def add(self, artifact: BuildArtifact) -> None:
        if any(item.output == artifact.output for item in self.artifacts):
            raise ValueError(f"duplicate build output: {artifact.output}")
        self.artifacts.append(artifact)

    def outputs(self) -> tuple[str, ...]:
        return tuple(sorted(item.output for item in self.artifacts))

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [
                {
                    "source": item.source,
                    "output": item.output,
                    "kind": item.kind,
                    "checksum": item.checksum,
                }
                for item in self.artifacts
            ]
        }
