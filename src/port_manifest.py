"""Port manifest builder for the Python porting workspace."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PortManifest:
    total_python_files: int
    top_level_modules: list[str]
    root_path: Path


def build_port_manifest(root: Path | None = None) -> PortManifest:
    """Scan *root* (defaults to the repository root) and return a manifest."""
    if root is None:
        root = Path(__file__).resolve().parent.parent

    python_files = sorted(root.rglob("*.py"))
    total = len(python_files)

    top_level: list[str] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "__init__.py").exists():
            top_level.append(child.name)
        elif child.suffix == ".py":
            top_level.append(child.stem)

    return PortManifest(
        total_python_files=total,
        top_level_modules=top_level,
        root_path=root,
    )
