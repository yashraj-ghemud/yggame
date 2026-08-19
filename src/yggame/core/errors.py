# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Typed errors raised by yggame.

Keeping errors in one small module makes it possible for applications and plugins to
handle configuration, asset, lifecycle, and optional-dependency failures precisely.
"""

from __future__ import annotations


class YggameError(Exception):
    """Base class for all expected yggame errors."""


class ConfigurationError(YggameError):
    """Raised when a configuration value is missing or invalid."""


class LifecycleError(YggameError):
    """Raised when an object is used outside its valid lifecycle."""


class AssetError(YggameError):
    """Raised when an asset cannot be loaded, decoded, or validated."""


class SerializationError(YggameError):
    """Raised for invalid or incompatible serialized data."""


class DependencyUnavailableError(YggameError):
    """Raised when an optional integration is requested but not installed."""


class RegistrationError(YggameError):
    """Raised when an extension or component registration is invalid."""
