"""Routing utilities for the Python porting workspace."""
from __future__ import annotations

from src.query_engine import QueryEnginePort


def route_query(query: str, limit: int = 10) -> list[tuple[str, object]]:
    """Route *query* and return a list of (kind, entry) tuples."""
    engine = QueryEnginePort.from_workspace()
    return engine.route(query, limit=limit)
