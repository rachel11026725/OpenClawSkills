"""Shared type definitions for the Python porting workspace."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EntryRef:
    """A lightweight reference to a command or tool entry."""

    kind: str  # 'command' or 'tool'
    name: str
    metadata: dict[str, Any] | None = None
