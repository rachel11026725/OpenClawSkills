"""Workspace configuration for the Python porting workspace."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WorkspaceConfig:
    root: Path = field(default_factory=lambda: Path(".").resolve())
    session_dir: Path = field(default_factory=lambda: Path(".") / ".sessions")
    archive_dir: Path = field(default_factory=lambda: Path(".") / "archive")
    max_sessions: int = 100
    default_limit: int = 10


_default_config: WorkspaceConfig | None = None


def get_config() -> WorkspaceConfig:
    global _default_config
    if _default_config is None:
        _default_config = WorkspaceConfig()
    return _default_config
