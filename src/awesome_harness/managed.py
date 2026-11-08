"""Plan and apply harness-owned runtime projections without clobbering user files."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from awesome_harness.config import HarnessConfig, load_config

Action = Literal["create", "update", "delete", "noop", "conflict"]
_STATE_PATH = Path(".harness/managed-state.json")
_PLUGIN_PATH = Path(".opencode/plugins/awesome-harness/index.ts")


class ManagedStateError(ValueError):
    """Managed state is malformed or cannot be applied safely."""


@dataclass(frozen=True)
class PlannedChange:
    path: Path
    action: Action
    reason: str
    before_sha256: str | None
    after_sha256: str | None
    content: str | None

    def as_dict(self, root: Path) -> dict[str, str | None]:
        return {
            "path": self.path.relative_to(root).as_posix(),
            "action": self.action,
            "reason": self.reason,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
        }


@dataclass(frozen=True)
class ApplyResult:
    changes: tuple[PlannedChange, ...]
    written: tuple[Path, ...]


def plan(root: Path) -> tuple[PlannedChange, ...]:
    """Compare desired projections with disk and recorded ownership state."""
    root = root.resolve()
    config = load_config(root)
    managed = _load_state(root)
    projections = _projections(config)
    changes: list[PlannedChange] = []

    for relative_path, desired_content in projections:
        path = root / relative_path
        desired_hash = _sha256(desired_content)
        installed_hash = managed.get(relative_path.as_posix())
        current_hash = _file_hash(path)

        if current_hash == desired_hash:
            action: Action = "noop"
            reason = "projection already matches desired state"
        elif current_hash is None:
            action = "create"
            reason = "harness-owned projection is absent"
        elif installed_hash is None:
            action = "conflict"
            reason = "path exists but is not recorded as harness-owned"
        elif current_hash != installed_hash:
            action = "conflict"
            reason = "managed projection was edited after the last apply"
        else:
            action = "update"
            reason = "desired projection changed"

        changes.append(
            PlannedChange(
                path=path,
                action=action,
                reason=reason,
                before_sha256=current_hash,
                after_sha256=desired_hash,
                content=desired_content,
            )
        )

    desired_paths = {relative_path.as_posix() for relative_path, _ in projections}
    for stale_path, installed_hash in sorted(managed.items()):
        if stale_path in desired_paths:
            continue
        path = root / stale_path
        current_hash = _file_hash(path)
        if current_hash is None:
            action = "noop"
            reason = "disabled projection is already absent"
        elif current_hash == installed_hash:
            action = "delete"
            reason = "projection is no longer enabled in desired state"
        else:
            action = "conflict"
            reason = "disabled projection was edited after the last apply"
        changes.append(
            PlannedChange(
                path=path,
                action=action,
                reason=reason,
                before_sha256=current_hash,
                after_sha256=None,
                content=None,
            )
        )
    return tuple(changes)


def apply(root: Path) -> ApplyResult:
    """Write a conflict-free plan and update the ownership fingerprints."""
    root = root.resolve()
    changes = plan(root)
    conflicts = tuple(change for change in changes if change.action == "conflict")
    if conflicts:
        paths = ", ".join(str(change.path.relative_to(root)) for change in conflicts)
        raise ManagedStateError(f"refusing to overwrite drifted or user-owned paths: {paths}")

    state = _load_state(root)
    written: list[Path] = []
    for change in changes:
        if change.action in {"create", "update"}:
            if change.content is None or change.after_sha256 is None:
                raise ManagedStateError(f"invalid write plan for {change.path}")
            change.path.parent.mkdir(parents=True, exist_ok=True)
            change.path.write_text(change.content, encoding="utf-8")
            written.append(change.path)
        elif change.action == "delete":
            change.path.unlink()
            written.append(change.path)
        relative = change.path.relative_to(root).as_posix()
        if change.after_sha256 is None:
            state.pop(relative, None)
        else:
            state[relative] = change.after_sha256

    _write_state(root, state)
    return ApplyResult(changes=changes, written=tuple(written))


def status(root: Path) -> tuple[PlannedChange, ...]:
    """Return the same deterministic comparison used by plan and apply."""
    return plan(root)


def _projections(config: HarnessConfig) -> tuple[tuple[Path, str], ...]:
    projections: list[tuple[Path, str]] = []
    if config.opencode.enabled:
        projections.append((_PLUGIN_PATH, _opencode_plugin(config)))
    return tuple(projections)


def _opencode_plugin(config: HarnessConfig) -> str:
    include_drafts = "true" if config.norms.include_drafts else "false"
    norms_enabled = "true" if config.norms.enabled else "false"
    return f'''// Generated by awesome-harness-123. Edit harness.toml, then run `harness apply`.
import {{ execFile }} from "node:child_process"
import {{ promisify }} from "node:util"
import {{ Plugin }} from "@opencode/plugin"

const run = promisify(execFile)
const normsEnabled = {norms_enabled}
const includeDrafts = {include_drafts}

export default Plugin.define({{
  id: "awesome-harness",
  async setup(ctx) {{
    if (!normsEnabled) return
    await ctx.tool.transform((editor) => {{
      editor.add({{
        name: "norms_resolve",
        description: "Resolve repository coding norms for a bounded task scope.",
        input: {{
          type: "object",
          properties: {{
            area: {{ type: "string" }},
            language: {{ type: "string" }},
            path: {{ type: "string" }},
            task: {{ type: "string" }},
          }},
          additionalProperties: false,
        }},
        async execute(input) {{
          const values = input as Record<string, string>
          const args = ["norms", "resolve", ctx.location.directory]
          for (const key of ["area", "language", "path", "task"]) {{
            if (values[key]) args.push(`--${{key}}`, values[key])
          }}
          if (includeDrafts) args.push("--include-drafts")
          const {{ stdout }} = await run("harness", args, {{ maxBuffer: 1024 * 1024 }})
          return {{ content: stdout.trim() }}
        }},
      }})
    }})
  }},
}})
'''


def _load_state(root: Path) -> dict[str, str]:
    path = root / _STATE_PATH
    if not path.exists():
        return {}
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManagedStateError(f"cannot parse managed state {path}: {error}") from error
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ManagedStateError(f"invalid managed state: {path}")
    files = value.get("files")
    if not isinstance(files, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in files.items()
    ):
        raise ManagedStateError(f"invalid managed file map: {path}")
    return cast("dict[str, str]", files)


def _write_state(root: Path, files: dict[str, str]) -> None:
    path = root / _STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "files": dict(sorted(files.items()))}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_hash(path: Path) -> str | None:
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ManagedStateError(f"cannot read managed path {path}: {error}") from error
    return hashlib.sha256(content).hexdigest()


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
