"""Initialize portable harness metadata in a target repository."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG = """# awesome-harness configuration
version = 1
profile = "default"
"""


@dataclass(frozen=True)
class PlannedWrite:
    path: Path
    content: str


def plan_initialization(root: Path) -> tuple[PlannedWrite, ...]:
    """Return the files required for a minimal harness installation."""
    return (
        PlannedWrite(root / "harness.toml", DEFAULT_CONFIG),
        PlannedWrite(root / ".harness" / "README.md", _state_readme()),
    )


def initialize(root: Path, *, dry_run: bool = False) -> tuple[Path, ...]:
    """Create missing harness files without overwriting user content."""
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"target is not a directory: {root}")

    created: list[Path] = []
    for planned in plan_initialization(root):
        if planned.path.exists():
            continue
        created.append(planned.path)
        if dry_run:
            continue
        planned.path.parent.mkdir(parents=True, exist_ok=True)
        planned.path.write_text(planned.content, encoding="utf-8")
    return tuple(created)


def _state_readme() -> str:
    return """# Harness state

This directory holds repository-local harness state. Cache and run artifacts are ignored by Git;
reviewed checkpoints and configuration may be committed deliberately.
"""
