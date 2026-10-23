"""Validation checks for harness repositories."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def validate_repository(root: Path) -> tuple[Check, ...]:
    """Run deterministic, non-mutating repository checks."""
    root = root.resolve()
    checks = [
        Check("directory", root.is_dir(), str(root)),
        Check("README", (root / "README.md").is_file(), "README.md"),
        Check("agent instructions", (root / "AGENTS.md").is_file(), "AGENTS.md"),
        Check("project metadata", (root / "pyproject.toml").is_file(), "pyproject.toml"),
        Check(
            "Superset configuration",
            (root / ".superset" / "config.json").is_file(),
            ".superset/config.json",
        ),
    ]
    checks.append(_git_check(root))
    return tuple(checks)


def _git_check(root: Path) -> Check:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
        text=True,
    )
    detail = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    return Check("Git repository", result.returncode == 0, detail or "git unavailable")
