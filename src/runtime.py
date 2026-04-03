"""Runtime module for the Python porting workspace."""
from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.query_engine import QueryEnginePort


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class TurnResult:
    matched_tools: list
    output: str
    usage: TokenUsage
    stop_reason: str = "end_turn"


@dataclass
class PortSession:
    session_id: str
    prompt: str
    turn_result: TurnResult
    persisted_session_path: str
    startup_steps: list[str] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)


_SESSION_DIR = Path(tempfile.gettempdir()) / "openclaw_sessions"


def _ensure_session_dir() -> Path:
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return _SESSION_DIR


class PortRuntime:
    def __init__(self) -> None:
        self._engine = QueryEnginePort.from_workspace()

    def bootstrap_session(self, prompt: str, limit: int = 10) -> PortSession:
        """Bootstrap a session for *prompt* and persist it."""
        matches = self._engine.route(prompt, limit=limit)
        matched_tools = [entry for kind, entry in matches if kind == "tool"]
        # If no tools surfaced in the top-N, search tools directly
        if not matched_tools:
            matched_tools = self._engine.query_tools(prompt, limit=limit)

        # Fake token usage – simulate at least 1 input token
        input_tokens = max(1, len(prompt.split()))
        output_tokens = max(1, len(matches))

        turn_output = f"Prompt: {prompt}\nMatched {len(matches)} entries."
        turn = TurnResult(
            matched_tools=matched_tools,
            output=turn_output,
            usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        )

        session_id = f"session-{int(time.time() * 1000)}"
        session_dir = _ensure_session_dir()
        session_path = session_dir / f"{session_id}.json"

        startup_steps = [
            "Initialize query engine",
            "Route prompt to commands/tools",
            "Bootstrap turn result",
            "Persist session",
        ]

        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": turn_output},
        ]

        payload = {
            "session_id": session_id,
            "prompt": prompt,
            "messages": messages,
            "startup_steps": startup_steps,
            "turn": {
                "matched_tools": [t.name for t in matched_tools],
                "output": turn_output,
                "stop_reason": turn.stop_reason,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            },
        }
        session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return PortSession(
            session_id=session_id,
            prompt=prompt,
            turn_result=turn,
            persisted_session_path=str(session_path),
            startup_steps=startup_steps,
            messages=messages,
        )

    def load_session(self, session_id: str) -> dict:
        """Load a previously persisted session by its ID."""
        session_path = _ensure_session_dir() / f"{session_id}.json"
        if not session_path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        return json.loads(session_path.read_text(encoding="utf-8"))
