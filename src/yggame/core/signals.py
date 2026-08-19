# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Godot-style per-object signals built on the same safe dispatch semantics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

SignalHandler = Callable[..., Any]


@dataclass(slots=True)
class _Connection:
    token: int
    callback: SignalHandler
    once: bool


class Connection:
    __slots__ = ("_signal", "_token", "_cancelled")

    def __init__(self, signal: Signal, token: int) -> None:
        self._signal = signal
        self._token = token
        self._cancelled = False

    def disconnect(self) -> None:
        if not self._cancelled:
            self._signal.disconnect(self._token)
            self._cancelled = True

    cancel = disconnect

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()


class Signal:
    """A local signal that preserves subscription order and supports one-shot hooks."""

    def __init__(self) -> None:
        self._connections: list[_Connection] = []
        self._next_token = 1

    def connect(self, callback: SignalHandler, *, once: bool = False) -> Connection:
        connection = _Connection(self._next_token, callback, once)
        self._next_token += 1
        self._connections.append(connection)
        return Connection(self, connection.token)

    def once(self, callback: SignalHandler) -> Connection:
        return self.connect(callback, once=True)

    def disconnect(self, token: int) -> None:
        self._connections[:] = [item for item in self._connections if item.token != token]

    def emit(self, *args: Any, **kwargs: Any) -> None:
        for connection in tuple(self._connections):
            connection.callback(*args, **kwargs)
            if connection.once:
                self.disconnect(connection.token)

    def clear(self) -> None:
        self._connections.clear()

    def __bool__(self) -> bool:
        return bool(self._connections)


class SignalDispatcher:
    """Mixin exposing named signals through `on` and `emit_signal`."""

    def __init__(self) -> None:
        self._signals: dict[str, Signal] = {}

    def signal(self, name: str) -> Signal:
        if not name:
            raise ValueError("signal name cannot be empty")
        return self._signals.setdefault(name, Signal())

    def on(self, name: str, callback: SignalHandler, *, once: bool = False) -> Connection:
        return self.signal(name).connect(callback, once=once)

    def emit_signal(self, name: str, *args: Any, **kwargs: Any) -> None:
        if name in self._signals:
            self._signals[name].emit(*args, **kwargs)
