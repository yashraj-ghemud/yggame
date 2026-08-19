# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Plugin contracts and a safe in-process registry."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from yggame.core.errors import RegistrationError


@dataclass(frozen=True, slots=True)
class PluginInfo:
    namespace: str
    name: str
    version: str
    factory: Callable[..., Any]


class PluginRegistry:
    """Registry for community components with collision-resistant namespaces."""

    def __init__(self) -> None:
        self._plugins: dict[tuple[str, str], PluginInfo] = {}

    def register(
        self, namespace: str, name: str, factory: Callable[..., Any], *, version: str = "0.1.0"
    ) -> PluginInfo:
        if not namespace.isidentifier() or not name.isidentifier():
            raise RegistrationError("plugin namespace and name must be valid identifiers")
        key = (namespace, name)
        if key in self._plugins:
            raise RegistrationError(f"plugin already registered: {namespace}.{name}")
        info = PluginInfo(namespace, name, version, factory)
        self._plugins[key] = info
        return info

    def get(self, namespace: str, name: str) -> PluginInfo:
        try:
            return self._plugins[(namespace, name)]
        except KeyError as exc:
            raise KeyError(f"unknown plugin: {namespace}.{name}") from exc

    def create(self, namespace: str, name: str, *args: Any, **kwargs: Any) -> Any:
        return self.get(namespace, name).factory(*args, **kwargs)

    def list(self, namespace: str | None = None) -> tuple[PluginInfo, ...]:
        items: Iterable[PluginInfo] = self._plugins.values()
        if namespace is not None:
            items = (item for item in items if item.namespace == namespace)
        return tuple(sorted(items, key=lambda item: (item.namespace, item.name)))

    def unregister(self, namespace: str, name: str) -> None:
        self._plugins.pop((namespace, name), None)
