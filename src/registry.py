"""High-level registry facade for the Python porting workspace."""
from __future__ import annotations

from src.commands import PORTED_COMMANDS, CommandEntry
from src.tools import PORTED_TOOLS, ToolEntry


class Registry:
    """Unified registry that wraps commands and tools."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandEntry] = {c.name.lower(): c for c in PORTED_COMMANDS}
        self._tools: dict[str, ToolEntry] = {t.name.lower(): t for t in PORTED_TOOLS}

    @property
    def commands(self) -> list[CommandEntry]:
        return list(self._commands.values())

    @property
    def tools(self) -> list[ToolEntry]:
        return list(self._tools.values())

    def command(self, name: str) -> CommandEntry:
        key = name.lower()
        if key not in self._commands:
            raise KeyError(f"Command not found: {name!r}")
        return self._commands[key]

    def tool(self, name: str) -> ToolEntry:
        key = name.lower()
        if key not in self._tools:
            raise KeyError(f"Tool not found: {name!r}")
        return self._tools[key]
