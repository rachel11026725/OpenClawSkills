"""Filter helpers for commands and tools."""
from __future__ import annotations

from src.commands import CommandEntry
from src.tools import ToolEntry


def filter_commands(
    entries: list[CommandEntry],
    query: str | None = None,
    no_plugin: bool = False,
    limit: int | None = None,
) -> list[CommandEntry]:
    result = list(entries)
    if no_plugin:
        result = [e for e in result if not e.plugin]
    if query:
        q = query.lower()
        result = [e for e in result if q in e.name.lower() or q in e.description.lower()]
    if limit is not None:
        result = result[:limit]
    return result


def filter_tools(
    entries: list[ToolEntry],
    query: str | None = None,
    no_mcp: bool = False,
    simple_mode: bool = False,
    deny_prefix: str | None = None,
    limit: int | None = None,
) -> list[ToolEntry]:
    result = list(entries)
    if no_mcp:
        result = [e for e in result if not e.mcp]
    if simple_mode:
        result = [e for e in result if e.simple]
    if deny_prefix:
        prefix = deny_prefix.lower()
        result = [e for e in result if not e.name.lower().startswith(prefix)]
    if query:
        q = query.lower()
        result = [e for e in result if q in e.name.lower() or q in e.description.lower()]
    if limit is not None:
        result = result[:limit]
    return result
