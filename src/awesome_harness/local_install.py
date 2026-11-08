"""Keep a harness installation local without changing committed ignore policy."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

_STATE_PATH = Path(".harness/local-install.json")
_PRIVATE_DIRECTORIES = (Path(".harness"), Path("norms"))
_MANAGED_PLUGIN_DIRECTORY = Path(".opencode/plugins/awesome-harness")
_PROJECT_OWNED_ROOTS = {"docs", "evals"}


class LocalInstallError(ValueError):
    """Local Git exclusions cannot be installed safely."""


@dataclass(frozen=True)
class GitContext:
    top_level: Path
    exclude_path: Path
    target_prefix: Path


def git_context(root: Path) -> GitContext:
    """Resolve the target's Git root and clone-local exclude file."""
    root = root.resolve()
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel", "--git-path", "info/exclude"],
        capture_output=True,
        check=False,
        text=True,
    )
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) != 2:
        detail = result.stderr.strip() or "not inside a Git worktree"
        raise LocalInstallError(
            f"local initialization requires Git first ({detail}); run `git init` or use "
            "`harness init --tracked`"
        )
    top_level = Path(lines[0]).resolve()
    exclude_path = Path(lines[1])
    if not exclude_path.is_absolute():
        exclude_path = (root / exclude_path).resolve()
    try:
        target_prefix = root.relative_to(top_level)
    except ValueError as error:
        raise LocalInstallError(f"target {root} is outside Git worktree {top_level}") from error
    return GitContext(
        top_level=top_level,
        exclude_path=exclude_path,
        target_prefix=target_prefix,
    )


def private_directories_absent(root: Path) -> frozenset[Path]:
    """Capture which private namespaces can safely be excluded as whole directories."""
    return frozenset(path for path in _PRIVATE_DIRECTORIES if not (root / path).exists())


def enable_local_install(
    root: Path,
    initialized_paths: tuple[Path, ...],
    whole_directories: frozenset[Path],
) -> None:
    """Record newly owned paths and install their clone-local Git exclusions."""
    root = root.resolve()
    context = git_context(root)
    patterns = set(_load_patterns(root))
    for path in initialized_paths:
        relative = path.resolve().relative_to(root)
        if relative.parts and relative.parts[0] in _PROJECT_OWNED_ROOTS:
            continue
        directory = _owning_directory(relative, whole_directories)
        patterns.add(_pattern(context, directory or relative, directory=directory is not None))

    if Path(".harness") not in whole_directories:
        patterns.add(_pattern(context, _STATE_PATH, directory=False))
    _write_state(root, patterns)
    _write_exclude_block(context, patterns)


def record_managed_paths(root: Path, paths: tuple[Path, ...]) -> None:
    """Add successfully applied harness projections to an existing local installation."""
    root = root.resolve()
    if not is_local_install(root) or not paths:
        return
    context = git_context(root)
    patterns = set(_load_patterns(root))
    for path in paths:
        relative = path.resolve().relative_to(root)
        if relative == _MANAGED_PLUGIN_DIRECTORY or _MANAGED_PLUGIN_DIRECTORY in relative.parents:
            patterns.add(_pattern(context, _MANAGED_PLUGIN_DIRECTORY, directory=True))
        else:
            patterns.add(_pattern(context, relative, directory=False))
    _write_state(root, patterns)
    _write_exclude_block(context, patterns)


def disable_local_install(root: Path) -> None:
    """Remove this target's managed exclude block when tracked mode is requested."""
    root = root.resolve()
    state_path = root / _STATE_PATH
    if not state_path.exists():
        return
    context = git_context(root)
    _write_exclude_block(context, set())
    state_path.unlink()


def is_local_install(root: Path) -> bool:
    return (root.resolve() / _STATE_PATH).is_file()


def _owning_directory(relative: Path, whole_directories: frozenset[Path]) -> Path | None:
    for directory in whole_directories:
        if relative == directory or directory in relative.parents:
            return directory
    return None


def _pattern(context: GitContext, relative: Path, *, directory: bool) -> str:
    combined = context.target_prefix / relative
    rendered = f"/{combined.as_posix()}"
    return f"{rendered}/" if directory else rendered


def _load_patterns(root: Path) -> tuple[str, ...]:
    path = root / _STATE_PATH
    if not path.exists():
        return ()
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LocalInstallError(f"cannot parse local install state {path}: {error}") from error
    if not isinstance(raw, dict) or raw.get("version") != 1 or raw.get("mode") != "local":
        raise LocalInstallError(f"invalid local install state: {path}")
    patterns = raw.get("patterns")
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        raise LocalInstallError(f"invalid local exclusion patterns: {path}")
    return tuple(cast("list[str]", patterns))


def _write_state(root: Path, patterns: set[str]) -> None:
    path = root / _STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "mode": "local", "patterns": sorted(patterns)}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_exclude_block(context: GitContext, patterns: set[str]) -> None:
    path = context.exclude_path
    try:
        current = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as error:
        raise LocalInstallError(f"cannot read Git exclude file {path}: {error}") from error

    key = context.target_prefix.as_posix() or "."
    begin = f"# BEGIN awesome-harness-123:{key}"
    end = f"# END awesome-harness-123:{key}"
    begin_count = current.count(begin)
    end_count = current.count(end)
    if begin_count != end_count or begin_count > 1:
        raise LocalInstallError(f"malformed harness block in {path}")

    if begin_count == 1:
        start = current.index(begin)
        finish = current.index(end, start) + len(end)
        before = current[:start].rstrip("\n")
        after = current[finish:].strip("\n")
    else:
        before = current.rstrip("\n")
        after = ""

    sections = [section for section in (before, after) if section]
    if patterns:
        block_lines = (
            begin,
            "# Managed by harness; edit installation mode, not this block.",
            *sorted(patterns),
            end,
        )
        block = "\n".join(block_lines)
        sections.append(block)
    rendered = "\n\n".join(sections)
    if rendered:
        rendered += "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    except OSError as error:
        raise LocalInstallError(f"cannot update Git exclude file {path}: {error}") from error
