"""Query engine port for the Python porting workspace."""
from __future__ import annotations

from dataclasses import dataclass

from src.commands import PORTED_COMMANDS
from src.tools import PORTED_TOOLS


@dataclass
class QueryEnginePort:
    commands: list
    tools: list

    @classmethod
    def from_workspace(cls) -> "QueryEnginePort":
        return cls(commands=list(PORTED_COMMANDS), tools=list(PORTED_TOOLS))

    def query_commands(self, q: str, limit: int = 10) -> list:
        terms = [t for t in q.lower().split() if t]
        results = [
            c for c in self.commands
            if any(term in (c.name + " " + c.description).lower() for term in terms)
        ]
        return results[:limit]

    def query_tools(self, q: str, limit: int = 10) -> list:
        terms = [t for t in q.lower().split() if t]
        results = [
            t for t in self.tools
            if any(term in (t.name + " " + t.description).lower() for term in terms)
        ]
        return results[:limit]

    def route(self, query: str, limit: int = 10) -> list:
        """Return a combined ranked list of commands and tools matching *query*.

        Each word in *query* is matched independently so that multi-word
        queries like 'review MCP tool' still return relevant entries.
        """
        terms = [t for t in query.lower().split() if t]
        results = []
        for entry in self.commands:
            haystack = (entry.name + " " + entry.description).lower()
            if any(term in haystack for term in terms):
                results.append(("command", entry))
        for entry in self.tools:
            haystack = (entry.name + " " + entry.description).lower()
            if any(term in haystack for term in terms):
                results.append(("tool", entry))
        return results[:limit]

    def render_summary(self) -> str:
        lines = [
            "Python Porting Workspace Summary",
            "=" * 40,
            f"Command surface: {len(self.commands)} entries",
            f"Tool surface: {len(self.tools)} entries",
        ]
        return "\n".join(lines)
