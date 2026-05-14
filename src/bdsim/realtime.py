"""Realtime public entry points.

This module provides a stable import path for realtime execution features
without requiring users to import the broader offline runner namespace.
"""

from .run_realtime import BDRealTime

__all__ = ["BDRealTime"]
