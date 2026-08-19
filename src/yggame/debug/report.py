# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Structured diagnostics reports for in-game overlays and CI artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .metrics import MetricSnapshot


@dataclass(frozen=True, slots=True)
class FrameSummary:
    frame: int
    real_delta: float
    simulation_delta: float
    updates: int
    interpolation: float
    fps: float

    @classmethod
    def from_frame(cls, frame_info: Any) -> FrameSummary:
        delta = max(1e-9, float(frame_info.real_delta))
        return cls(
            frame_info.frame,
            frame_info.real_delta,
            frame_info.simulation_delta,
            frame_info.updates,
            frame_info.interpolation,
            1.0 / delta,
        )


@dataclass(slots=True)
class DiagnosticsReport:
    title: str = "yggame diagnostics"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    frames: list[FrameSummary] = field(default_factory=list)
    metrics: list[MetricSnapshot] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_frame(self, summary: FrameSummary) -> None:
        self.frames.append(summary)

    def add_metrics(self, snapshot: MetricSnapshot) -> None:
        self.metrics.append(snapshot)

    def summary(self) -> dict[str, Any]:
        fps = [frame.fps for frame in self.frames]
        return {
            "title": self.title,
            "created_at": self.created_at,
            "frames": len(self.frames),
            "average_fps": sum(fps) / len(fps) if fps else 0.0,
            "minimum_fps": min(fps) if fps else 0.0,
            "maximum_fps": max(fps) if fps else 0.0,
            "metadata": self.metadata,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "frames": [asdict(frame) for frame in self.frames],
            "metrics": [
                {
                    "counters": metric.counters,
                    "gauges": metric.gauges,
                    "timings_ms": metric.timings_ms,
                }
                for metric in self.metrics
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, sort_keys=True)
