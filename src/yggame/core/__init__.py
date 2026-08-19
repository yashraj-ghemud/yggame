# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Core runtime contracts for yggame."""

from .clock import Clock, Cooldown, RealTimeSource, Stopwatch, Timer
from .config import Config
from .context import BaseSystem, Drawable, GameContext, Lifecycle, System
from .crash import CrashReport, CrashReporter
from .ecs import Entity, SystemScheduler, World
from .errors import (
    AssetError,
    ConfigurationError,
    DependencyUnavailableError,
    LifecycleError,
    RegistrationError,
    SerializationError,
    YggameError,
)
from .events import Event, EventBus, Subscription
from .game import FrameInfo, Game
from .geometry import Rect, Vec2, bounds, clamp, lerp, lerp_vec, move_toward
from .invariants import InvariantError, InvariantFailure, Invariants
from .pool import ObjectPool, PoolExhausted
from .recovery import Checkpoint, RecoveryManager, RetryExecutor, RetryPolicy
from .replay import InputFrame, Replay, ReplayPlayer, ReplayRecorder
from .resources import ResourceEntry, ResourceHandle, ResourceManager
from .rng import RandomStream, derive_seed, deterministic_id, weighted_choice
from .scheduler import (
    CommandBuffer,
    DeferredCommand,
    SystemGraph,
    SystemSpec,
    TaskHandle,
    TaskScheduler,
)
from .schema import Field, Schema, one_of, range_, sequence_of
from .serialization import CodecRegistry, TypeTag, dump_file, dumps, load_file, loads
from .signals import Connection, Signal, SignalDispatcher
from .telemetry import Breadcrumbs, Telemetry, TelemetryEvent

__all__ = [
    "AssetError",
    "CrashReport",
    "CrashReporter",
    "BaseSystem",
    "Clock",
    "Checkpoint",
    "RecoveryManager",
    "RetryExecutor",
    "RetryPolicy",
    "clamp",
    "Config",
    "ConfigurationError",
    "Connection",
    "Cooldown",
    "DependencyUnavailableError",
    "Drawable",
    "Entity",
    "Event",
    "EventBus",
    "FrameInfo",
    "Game",
    "GameContext",
    "InvariantError",
    "InvariantFailure",
    "Invariants",
    "lerp",
    "lerp_vec",
    "Lifecycle",
    "LifecycleError",
    "move_toward",
    "ObjectPool",
    "PoolExhausted",
    "RealTimeSource",
    "RandomStream",
    "derive_seed",
    "deterministic_id",
    "weighted_choice",
    "Rect",
    "InputFrame",
    "Replay",
    "ReplayPlayer",
    "ReplayRecorder",
    "RegistrationError",
    "ResourceEntry",
    "ResourceHandle",
    "ResourceManager",
    "SerializationError",
    "Signal",
    "SignalDispatcher",
    "Stopwatch",
    "Breadcrumbs",
    "Telemetry",
    "TelemetryEvent",
    "Subscription",
    "System",
    "SystemScheduler",
    "Timer",
    "TypeTag",
    "Vec2",
    "World",
    "YggameError",
    "CodecRegistry",
    "CommandBuffer",
    "DeferredCommand",
    "dump_file",
    "dumps",
    "load_file",
    "loads",
    "SystemGraph",
    "SystemSpec",
    "TaskHandle",
    "TaskScheduler",
    "Field",
    "Schema",
    "one_of",
    "range_",
    "sequence_of",
    "bounds",
]
