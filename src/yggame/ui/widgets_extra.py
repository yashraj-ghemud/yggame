# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Higher-level UI widgets built on the retained-mode base."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from yggame.core.clock import Timer
from yggame.core.geometry import Rect, clamp

from .base import UIElement, UIEvent


class Toggle(UIElement):
    def __init__(self, value: bool = False, rect: Rect | None = None, *, label: str = "") -> None:
        super().__init__(rect or Rect(0, 0, 48, 28), name=label)
        self.value = value
        self.label = label
        self.focusable = True
        self.on("event:mouse_up", self._activate)
        self.on("event:key_down", self._key_activate)

    def set_value(self, value: bool, *, emit: bool = True) -> None:
        value = bool(value)
        if value == self.value:
            return
        previous = self.value
        self.value = value
        if emit:
            self.emit_signal("changed", value, previous)

    def toggle(self) -> None:
        self.set_value(not self.value)

    def _activate(self, event: UIEvent) -> None:
        if event.position and self.rect.contains(event.position):
            self.toggle()
            event.consume()

    def _key_activate(self, event: UIEvent) -> None:
        if event.key in {"enter", "space"}:
            self.toggle()
            event.consume()


class Checkbox(Toggle):
    def __init__(self, label: str, value: bool = False, rect: Rect | None = None) -> None:
        super().__init__(value, rect or Rect(0, 0, 220, 28), label=label)


@dataclass(frozen=True, slots=True)
class SelectOption:
    value: Any
    label: str
    disabled: bool = False


class Dropdown(UIElement):
    def __init__(self, options: Iterable[SelectOption], rect: Rect | None = None) -> None:
        super().__init__(rect or Rect(0, 0, 180, 36))
        self.options = list(options)
        self.selected_index = next(
            (index for index, option in enumerate(self.options) if not option.disabled), -1
        )
        self.open = False
        self.focusable = True

    @property
    def selected(self) -> SelectOption | None:
        return (
            self.options[self.selected_index]
            if 0 <= self.selected_index < len(self.options)
            else None
        )

    def set_options(self, options: Iterable[SelectOption]) -> None:
        self.options = list(options)
        self.selected_index = next(
            (index for index, option in enumerate(self.options) if not option.disabled), -1
        )

    def select(self, index: int) -> None:
        if not 0 <= index < len(self.options):
            raise IndexError("dropdown option outside bounds")
        option = self.options[index]
        if option.disabled:
            return
        previous = self.selected
        self.selected_index = index
        self.open = False
        self.emit_signal("changed", option, previous)

    def handle(self, event: UIEvent) -> bool:
        if event.type == "mouse_down" and event.position and self.rect.contains(event.position):
            self.open = not self.open
            event.consume()
        elif event.type == "key_down" and self.focused:
            if event.key in {"enter", "space"}:
                self.open = not self.open
                event.consume()
            elif self.open and event.key in {"up", "down"}:
                self._move(-1 if event.key == "up" else 1)
                event.consume()
        return super().handle(event)

    def _move(self, amount: int) -> None:
        if not self.options:
            return
        index = self.selected_index
        for _ in range(len(self.options)):
            index = (index + amount) % len(self.options)
            if not self.options[index].disabled:
                self.select(index)
                return


class TextInputField(UIElement):
    def __init__(
        self,
        text: str = "",
        rect: Rect | None = None,
        *,
        placeholder: str = "",
        max_length: int | None = None,
        validator: Callable[[str], bool] | None = None,
    ) -> None:
        super().__init__(rect or Rect(0, 0, 240, 36))
        if max_length is not None and max_length < 0:
            raise ValueError("max_length cannot be negative")
        self.text = text
        self.placeholder = placeholder
        self.max_length = max_length
        self.validator = validator
        self.cursor = len(text)
        self.focusable = True
        self._blink = Timer(0.5, repeat=True)
        self.cursor_visible = True

    def set_text(self, text: str, *, emit: bool = True) -> None:
        if self.max_length is not None:
            text = text[: self.max_length]
        if self.validator and not self.validator(text):
            return
        previous = self.text
        self.text = text
        self.cursor = min(self.cursor, len(text))
        if emit and text != previous:
            self.emit_signal("changed", text, previous)

    def insert(self, text: str) -> None:
        candidate = self.text[: self.cursor] + text + self.text[self.cursor :]
        previous = self.text
        if self.max_length is not None:
            candidate = candidate[: self.max_length]
        if self.validator and not self.validator(candidate):
            return
        self.text = candidate
        self.cursor = min(len(candidate), self.cursor + len(text))
        if self.text != previous:
            self.emit_signal("changed", self.text, previous)

    def delete_backward(self) -> None:
        if self.cursor <= 0:
            return
        self.set_text(self.text[: self.cursor - 1] + self.text[self.cursor :])
        self.cursor -= 1

    def handle(self, event: UIEvent) -> bool:
        if event.type == "text_input" and event.text is not None and self.focused:
            self.insert(event.text)
            event.consume()
        elif event.type == "key_down" and self.focused:
            self._handle_key(event)
        return super().handle(event)

    def _handle_key(self, event: UIEvent) -> None:
        if event.key == "backspace":
            self.delete_backward()
        elif event.key == "left":
            self.cursor = max(0, self.cursor - 1)
        elif event.key == "right":
            self.cursor = min(len(self.text), self.cursor + 1)
        elif event.key == "home":
            self.cursor = 0
        elif event.key == "end":
            self.cursor = len(self.text)
        else:
            return
        self.cursor_visible = True
        self._blink.reset()

    def update(self, delta: float) -> None:
        super().update(delta)
        if self._blink.update(delta):
            self.cursor_visible = not self.cursor_visible


class Tooltip(UIElement):
    def __init__(self, text: str, *, delay: float = 0.5, rect: Rect | None = None) -> None:
        super().__init__(rect or Rect(0, 0, 0, 0))
        if delay < 0:
            raise ValueError("tooltip delay cannot be negative")
        self.text = text
        self.delay = delay
        self.visible = False
        self._timer = 0.0
        self._source: UIElement | None = None

    def attach(self, source: UIElement) -> None:
        self._source = source
        source.on("hover_enter", self._enter)
        source.on("hover_exit", self._exit)

    def _enter(self, *_: Any) -> None:
        self._timer = 0.0

    def _exit(self, *_: Any) -> None:
        self.visible = False
        self._timer = 0.0

    def update(self, delta: float) -> None:
        super().update(delta)
        if self._source and self._source.hovered:
            self._timer += max(0.0, delta)
            self.visible = self._timer >= self.delay


class Modal(UIElement):
    def __init__(self, rect: Rect, *, dismiss_on_escape: bool = True) -> None:
        super().__init__(rect)
        self.dismiss_on_escape = dismiss_on_escape
        self.focusable = True
        self.on_close: Callable[[], None] | None = None

    def close(self) -> None:
        self.visible = False
        if self.on_close:
            self.on_close()
        self.emit_signal("closed")

    def handle(self, event: UIEvent) -> bool:
        if event.type == "key_down" and event.key == "escape" and self.dismiss_on_escape:
            self.close()
            event.consume()
            return True
        return super().handle(event)


@dataclass(slots=True)
class ToastMessage:
    message: str
    duration: float = 3.0
    elapsed: float = 0.0
    severity: str = "info"

    @property
    def expired(self) -> bool:
        return self.elapsed >= self.duration


class ToastQueue(UIElement):
    def __init__(self, rect: Rect | None = None, *, maximum: int = 5) -> None:
        super().__init__(rect or Rect(0, 0, 360, 400))
        if maximum <= 0:
            raise ValueError("toast maximum must be positive")
        self.maximum = maximum
        self.messages: list[ToastMessage] = []

    def push(self, message: str, *, duration: float = 3.0, severity: str = "info") -> ToastMessage:
        if duration <= 0:
            raise ValueError("toast duration must be positive")
        item = ToastMessage(message, duration, severity=severity)
        self.messages.append(item)
        del self.messages[: -self.maximum]
        self.emit_signal("pushed", item)
        return item

    def update(self, delta: float) -> None:
        super().update(delta)
        for item in self.messages:
            item.elapsed += max(0.0, delta)
        expired = [item for item in self.messages if item.expired]
        self.messages[:] = [item for item in self.messages if not item.expired]
        for item in expired:
            self.emit_signal("expired", item)


class SelectList(UIElement):
    def __init__(self, items: Iterable[Any] = (), rect: Rect | None = None) -> None:
        super().__init__(rect or Rect(0, 0, 260, 240))
        self.items = list(items)
        self.selected_index = -1
        self.scroll_offset = 0
        self.focusable = True

    @property
    def selected(self) -> Any | None:
        return (
            self.items[self.selected_index] if 0 <= self.selected_index < len(self.items) else None
        )

    def set_items(self, items: Iterable[Any]) -> None:
        self.items = list(items)
        self.selected_index = min(self.selected_index, len(self.items) - 1)

    def select(self, index: int) -> Any:
        if not 0 <= index < len(self.items):
            raise IndexError("list index outside bounds")
        previous = self.selected
        self.selected_index = index
        self.emit_signal("changed", self.items[index], previous)
        return self.items[index]

    def handle(self, event: UIEvent) -> bool:
        if event.type == "key_down" and self.focused and event.key in {"up", "down"}:
            amount = -1 if event.key == "up" else 1
            index = clamp(self.selected_index + amount, 0, max(0, len(self.items) - 1))
            if self.items:
                self.select(int(index))
            event.consume()
        return super().handle(event)
