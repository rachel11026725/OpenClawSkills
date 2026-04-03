"""Execution registry for the Python porting workspace."""
from __future__ import annotations

from dataclasses import dataclass

from src.commands import PORTED_COMMANDS, CommandEntry
from src.tools import PORTED_TOOLS, ToolEntry


@dataclass
class ExecutionRegistry:
    commands: list[CommandEntry]
    tools: list[ToolEntry]

    def command(self, name: str) -> CommandEntry:
        name_lower = name.lower()
        for cmd in self.commands:
            if cmd.name.lower() == name_lower:
                return cmd
        raise KeyError(f"Command not found: {name!r}")

    def tool(self, name: str) -> ToolEntry:
        name_lower = name.lower()
        for t in self.tools:
            if t.name.lower() == name_lower:
                return t
        raise KeyError(f"Tool not found: {name!r}")


def build_execution_registry() -> ExecutionRegistry:
    return ExecutionRegistry(
        commands=list(PORTED_COMMANDS),
        tools=list(PORTED_TOOLS),
    )
