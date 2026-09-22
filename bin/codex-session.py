#!/usr/bin/env python3
"""Backward-compatible entry point for the unified session adapter."""

from pathlib import Path
import runpy


runpy.run_path(str(Path(__file__).with_name("session-adapter.py")), run_name="__main__")
