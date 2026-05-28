#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility shim for moved block classes.

Core block classes (Block, SinkBlock, SourceBlock, …) live in bdsim.block.
GraphicsBlock and notebook/MPL support live in bdsim.graphics_block.
"""

from bdsim.block import (
    Block,
    SinkBlock,
    SourceBlock,
    ContinuousBlock,
    FunctionBlock,
    SubsystemBlock,
    SampledBlock,
    EventSource,
)
from bdsim.graphics_block import GraphicsBlock

__all__ = [
    "Block",
    "SinkBlock",
    "SourceBlock",
    "ContinuousBlock",
    "FunctionBlock",
    "SubsystemBlock",
    "SampledBlock",
    "EventSource",
    "GraphicsBlock",
]
