# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Animation and tweening."""

from .controller import AnimationClip, AnimationController, AnimationFrame, TransitionRule
from .graph import (
    AnimationGraph,
    AnimationParameter,
    Blend1D,
    BlendSample,
    GraphState,
    GraphTransition,
    ParameterType,
    RootMotion,
)
from .tween import (
    EASINGS,
    PropertyTween,
    Tween,
    ease_in_out_quad,
    ease_in_quad,
    ease_out_back,
    ease_out_bounce,
    ease_out_quad,
    linear,
)

__all__ = [
    "AnimationClip",
    "AnimationController",
    "AnimationFrame",
    "AnimationGraph",
    "AnimationParameter",
    "Blend1D",
    "BlendSample",
    "EASINGS",
    "GraphState",
    "GraphTransition",
    "ParameterType",
    "PropertyTween",
    "RootMotion",
    "TransitionRule",
    "Tween",
    "ease_in_out_quad",
    "ease_in_quad",
    "ease_out_back",
    "ease_out_bounce",
    "ease_out_quad",
    "linear",
]
