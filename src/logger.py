"""Simple structured logger for the Python porting workspace."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkspaceLogger:
    name: str
    records: list[dict[str, Any]] = field(default_factory=list)
    verbose: bool = False

    def info(self, msg: str, **kwargs: Any) -> None:
        record = {"level": "INFO", "name": self.name, "msg": msg, **kwargs}
        self.records.append(record)
        if self.verbose:
            print(f"[INFO] {self.name}: {msg}", file=sys.stderr)

    def warning(self, msg: str, **kwargs: Any) -> None:
        record = {"level": "WARNING", "name": self.name, "msg": msg, **kwargs}
        self.records.append(record)
        if self.verbose:
            print(f"[WARNING] {self.name}: {msg}", file=sys.stderr)

    def error(self, msg: str, **kwargs: Any) -> None:
        record = {"level": "ERROR", "name": self.name, "msg": msg, **kwargs}
        self.records.append(record)
        print(f"[ERROR] {self.name}: {msg}", file=sys.stderr)


def get_logger(name: str, verbose: bool = False) -> WorkspaceLogger:
    return WorkspaceLogger(name=name, verbose=verbose)
