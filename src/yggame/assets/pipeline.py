# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Asset descriptors and content-pipeline validation helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from yggame.core.errors import AssetError


@dataclass(frozen=True, slots=True)
class AtlasRegion:
    name: str
    x: int
    y: int
    width: int
    height: int
    pivot: tuple[float, float] = (0.5, 0.5)
    nine_slice: tuple[int, int, int, int] | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("atlas region dimensions must be positive")
        if not all(0 <= value <= 1 for value in self.pivot):
            raise ValueError("atlas pivot values must be between zero and one")


@dataclass(slots=True)
class Atlas:
    image: str
    regions: dict[str, AtlasRegion] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, region: AtlasRegion) -> None:
        if region.name in self.regions:
            raise ValueError(f"duplicate atlas region: {region.name}")
        self.regions[region.name] = region

    def get(self, name: str) -> AtlasRegion:
        try:
            return self.regions[name]
        except KeyError as exc:
            raise AssetError(f"unknown atlas region: {name}") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "image": self.image,
            "regions": {
                name: {
                    "x": region.x,
                    "y": region.y,
                    "width": region.width,
                    "height": region.height,
                    "pivot": list(region.pivot),
                    "nine_slice": region.nine_slice,
                }
                for name, region in self.regions.items()
            },
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Atlas:
        atlas = cls(str(value["image"]), metadata=dict(value.get("metadata", {})))
        for name, raw in value.get("regions", {}).items():
            atlas.add(
                AtlasRegion(
                    name,
                    int(raw["x"]),
                    int(raw["y"]),
                    int(raw["width"]),
                    int(raw["height"]),
                    tuple(raw.get("pivot", (0.5, 0.5))),
                    tuple(raw["nine_slice"]) if raw.get("nine_slice") else None,
                )
            )
        return atlas


@dataclass(frozen=True, slots=True)
class AssetDependency:
    path: str
    kind: str
    required: bool = True
    checksum: str | None = None


@dataclass(slots=True)
class AssetManifest:
    name: str
    version: str = "1.0.0"
    dependencies: list[AssetDependency] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, dependency: AssetDependency) -> None:
        if any(item.path == dependency.path for item in self.dependencies):
            raise ValueError(f"duplicate asset dependency: {dependency.path}")
        self.dependencies.append(dependency)

    def validate(self, root: str | Path) -> list[str]:
        root = Path(root)
        errors: list[str] = []
        for dependency in self.dependencies:
            path = root / dependency.path
            if not path.exists():
                message = f"missing {dependency.kind} asset: {dependency.path}"
                if dependency.required:
                    errors.append(message)
        return errors

    def to_json(self) -> str:
        return json.dumps(
            {
                "name": self.name,
                "version": self.version,
                "dependencies": [asdict(dependency) for dependency in self.dependencies],
                "metadata": self.metadata,
            },
            indent=2,
            sort_keys=True,
        )


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: str
    message: str
    severity: str = "error"


class ContentValidator:
    """Validates asset manifests and JSON content with small reusable rules."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def validate_manifest(
        self, manifest: AssetManifest, root: str | Path
    ) -> tuple[ValidationIssue, ...]:
        self.issues.clear()
        for error in manifest.validate(root):
            self.issues.append(ValidationIssue(manifest.name, error))
        return tuple(self.issues)

    def require_keys(self, value: dict[str, Any], path: str, keys: Iterable[str]) -> None:
        for key in keys:
            if key not in value:
                self.issues.append(ValidationIssue(f"{path}.{key}", "required key is missing"))

    def unique_ids(self, values: Iterable[dict[str, Any]], path: str) -> None:
        seen: set[Any] = set()
        for index, value in enumerate(values):
            item_id = value.get("id")
            if item_id in seen:
                self.issues.append(
                    ValidationIssue(f"{path}[{index}]", f"duplicate id: {item_id!r}")
                )
            seen.add(item_id)

    def raise_if_invalid(self) -> None:
        errors = [item for item in self.issues if item.severity == "error"]
        if errors:
            message = "; ".join(f"{item.path}: {item.message}" for item in errors)
            raise AssetError(message)
