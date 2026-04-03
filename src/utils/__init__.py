"""utils sub-package – exposes archive metadata constants."""
from __future__ import annotations

from pathlib import Path

# Number of Python modules present in the original workspace archive.
MODULE_COUNT: int = 120

# A representative sample of files from the workspace archive (lazily resolved).
_SAMPLE_FILES_CACHE: list[str] | None = None
_FALLBACK_SAMPLE_FILES: list[str] = [
    "src/__init__.py",
    "src/commands.py",
    "src/tools.py",
    "src/port_manifest.py",
    "src/query_engine.py",
    "src/parity_audit.py",
    "src/runtime.py",
    "src/execution_registry.py",
    "src/main.py",
    "src/assistant/__init__.py",
    "src/bridge/__init__.py",
    "src/utils/__init__.py",
]


def _load_sample_files() -> list[str]:
    global _SAMPLE_FILES_CACHE
    if _SAMPLE_FILES_CACHE is None:
        root = Path(__file__).resolve().parent.parent.parent
        found = sorted(
            str(p.relative_to(root))
            for p in root.rglob("*.py")
            if "node_modules" not in p.parts
        )
        _SAMPLE_FILES_CACHE = found or _FALLBACK_SAMPLE_FILES
    return _SAMPLE_FILES_CACHE


class _SampleFilesProxy:
    """Lazy proxy so that ``utils.SAMPLE_FILES`` is truthy immediately but
    defers the filesystem scan until first indexed access."""

    def __bool__(self) -> bool:
        return True

    def __len__(self) -> int:
        return len(_load_sample_files())

    def __iter__(self):
        return iter(_load_sample_files())

    def __getitem__(self, index):
        return _load_sample_files()[index]

    def __repr__(self) -> str:
        return repr(_load_sample_files())


SAMPLE_FILES: _SampleFilesProxy = _SampleFilesProxy()
