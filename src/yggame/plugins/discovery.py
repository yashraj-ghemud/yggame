# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Plugin manifests and deterministic dependency-aware activation."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any

from yggame.core.errors import RegistrationError

from .registry import PluginRegistry


@dataclass(frozen=True, slots=True)
class PluginManifest:
    namespace: str
    name: str
    version: str
    module: str
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.namespace}.{self.name}"


class PluginManager:
    def __init__(self, registry: PluginRegistry | None = None) -> None:
        self.registry = registry or PluginRegistry()
        self.manifests: dict[str, PluginManifest] = {}
        self.active: set[str] = set()

    def add_manifest(self, manifest: PluginManifest) -> None:
        if manifest.key in self.manifests:
            raise RegistrationError(f"duplicate plugin manifest: {manifest.key}")
        self.manifests[manifest.key] = manifest

    def activation_order(self) -> tuple[str, ...]:
        pending = set(self.manifests)
        result: list[str] = []
        while pending:
            ready = sorted(
                key
                for key in pending
                if all(
                    dependency in result or dependency not in self.manifests
                    for dependency in self.manifests[key].dependencies
                )
            )
            if not ready:
                raise RegistrationError(
                    "plugin dependency graph contains a cycle or missing dependency"
                )
            result.extend(ready)
            pending.difference_update(ready)
        return tuple(result)

    def load_all(self) -> tuple[str, ...]:
        loaded: list[str] = []
        for key in self.activation_order():
            manifest = self.manifests[key]
            try:
                module = importlib.import_module(manifest.module)
                initializer = getattr(module, "register", None)
                if initializer is None:
                    raise RegistrationError(
                        f"plugin module has no register(registry) function: {manifest.module}"
                    )
                initializer(self.registry)
            except Exception as exc:
                raise RegistrationError(f"failed to load plugin {key}: {exc}") from exc
            self.active.add(key)
            loaded.append(key)
        return tuple(loaded)

    def deactivate(self, key: str) -> None:
        self.active.discard(key)

    def clear(self) -> None:
        self.active.clear()
        self.manifests.clear()
