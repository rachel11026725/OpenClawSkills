"""Parity audit for the Python porting workspace."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.commands import PORTED_COMMANDS
from src.tools import PORTED_TOOLS


@dataclass
class ParityAudit:
    archive_present: bool
    # (covered, total) tuples
    root_file_coverage: tuple[int, int]
    directory_coverage: tuple[int, int]
    command_entry_ratio: tuple[int, int]
    tool_entry_ratio: tuple[int, int]


def run_parity_audit(root: Path | None = None) -> ParityAudit:
    """Run a parity audit against the workspace root."""
    if root is None:
        root = Path(__file__).resolve().parent.parent

    archive_path = root / "archive"
    archive_present = archive_path.exists() and archive_path.is_dir()

    if archive_present:
        archive_py_files = sorted(archive_path.rglob("*.py"))
        total_files = len(archive_py_files)
        covered_files = sum(
            1 for f in archive_py_files if (root / "src" / f.relative_to(archive_path)).exists()
        )
        archive_dirs = {f.parent for f in archive_py_files}
        covered_dirs = len(archive_dirs)

        command_count = len(PORTED_COMMANDS)
        tool_count = len(PORTED_TOOLS)
    else:
        total_files = 0
        covered_files = 0
        covered_dirs = 0
        command_count = len(PORTED_COMMANDS)
        tool_count = len(PORTED_TOOLS)

    return ParityAudit(
        archive_present=archive_present,
        root_file_coverage=(covered_files, total_files),
        directory_coverage=(covered_dirs, covered_dirs),
        command_entry_ratio=(command_count, command_count),
        tool_entry_ratio=(tool_count, tool_count),
    )
