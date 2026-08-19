# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Structured crash-report data for local logs and support bundles."""

from __future__ import annotations

import platform
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .telemetry import Breadcrumbs, Telemetry


@dataclass(frozen=True, slots=True)
class CrashReport:
    error_type: str
    message: str
    traceback_text: str
    created_at: str
    platform: str
    python: str
    breadcrumbs: tuple[str, ...] = ()
    telemetry: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CrashReporter:
    def __init__(
        self, *, breadcrumbs: Breadcrumbs | None = None, telemetry: Telemetry | None = None
    ) -> None:
        self.breadcrumbs = breadcrumbs or Breadcrumbs()
        self.telemetry = telemetry or Telemetry()

    def capture(self, error: BaseException, **metadata: Any) -> CrashReport:
        self.telemetry.record("crash", error_type=type(error).__name__)
        return CrashReport(
            type(error).__name__,
            str(error),
            "".join(traceback.format_exception(error)),
            datetime.now(timezone.utc).isoformat(),
            platform.platform(),
            platform.python_version(),
            self.breadcrumbs.snapshot(),
            self.telemetry.export(),
            dict(metadata),
        )

    def install_hook(self) -> None:
        import sys

        def hook(
            error_type: type[BaseException], error: BaseException, traceback_object: Any
        ) -> None:
            report = self.capture(error)
            sys.stderr.write(f"yggame crash: {report.error_type}: {report.message}\n")
            sys.stderr.write(report.traceback_text)

        sys.excepthook = hook
