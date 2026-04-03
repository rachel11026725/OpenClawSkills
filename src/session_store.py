"""Session storage helpers for the Python porting workspace."""
from __future__ import annotations

import json
from pathlib import Path


class SessionStore:
    def __init__(self, store_dir: Path) -> None:
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, data: dict) -> Path:
        path = self.store_dir / f"{session_id}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def load(self, session_id: str) -> dict:
        path = self.store_dir / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_sessions(self) -> list[str]:
        return [p.stem for p in sorted(self.store_dir.glob("*.json"))]
