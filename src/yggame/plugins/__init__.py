# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Community plugin registration."""

from .discovery import PluginManager, PluginManifest
from .registry import PluginInfo, PluginRegistry

__all__ = ["PluginInfo", "PluginManager", "PluginManifest", "PluginRegistry"]
