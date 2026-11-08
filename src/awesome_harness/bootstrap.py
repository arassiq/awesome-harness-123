"""Initialize portable harness metadata in a target repository."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from awesome_harness.assets import baseline_assets

LEGACY_DEFAULT_CONFIG = """# awesome-harness configuration
version = 1
profile = "default"
"""

PRE_COMPACTION_DEFAULT_CONFIG = """# awesome-harness configuration
version = 1
profile = "default"

[runtimes.opencode]
enabled = true
version = "2.2.1"

[norms]
enabled = true
source = "norms"
include_drafts = false
"""

LEGACY_NORMS_README = """# Repository coding norms

Author reviewed, independently selectable rules here. Norms remain inactive until their
frontmatter status is `active`; initialization never invents project policy.

Validate the library with `harness norms validate` and preview task-specific selection with
`harness norms resolve --area AREA --language LANGUAGE --task TASK --path FILE`.
"""

LEGACY_NORMS_INDEX = """# Norm index

This human index starts empty. The harness builds its runtime index from validated norm metadata.
"""

DEFAULT_CONFIG = """# awesome-harness configuration
version = 1
profile = "default"

[runtimes.opencode]
enabled = true
version = "2.2.1"

[norms]
enabled = true
source = "norms"
include_drafts = false

[compaction]
# Experimental until the OpenCode adapter can install a structured replacement window.
enabled = false
strategy = "cliff"
# Harness hypotheses to evaluate; the Cliff paper does not prescribe these two values.
trigger_percent = 60
recent_turn_pairs = 8
tool_result_max_chars = 500
tool_signature_max_chars = 150
reasoning_max_chars = 300
"""


@dataclass(frozen=True)
class PlannedWrite:
    path: Path
    content: str


def plan_initialization(
    root: Path, *, private_scaffold: bool = False
) -> tuple[PlannedWrite, ...]:
    """Return the portable baseline files for a harness installation."""
    base = (
        PlannedWrite(root / "harness.toml", DEFAULT_CONFIG),
        PlannedWrite(root / ".harness" / "README.md", _state_readme()),
        PlannedWrite(root / ".harness" / ".gitignore", _state_gitignore()),
    )
    assets = tuple(
        PlannedWrite(root / asset.destination, asset.content)
        for asset in baseline_assets(private_scaffold=private_scaffold)
    )
    return base + assets


def initialize(
    root: Path, *, dry_run: bool = False, private_scaffold: bool = False
) -> tuple[Path, ...]:
    """Create missing harness files without overwriting user content."""
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"target is not a directory: {root}")

    alternate_agents = next(
        asset.content
        for asset in baseline_assets(private_scaffold=not private_scaffold)
        if asset.destination == Path("AGENTS.md")
    )
    created: list[Path] = []
    for planned in plan_initialization(root, private_scaffold=private_scaffold):
        if planned.path.exists():
            known_previous: set[str] = set()
            if planned.path == root / "harness.toml":
                known_previous = {LEGACY_DEFAULT_CONFIG, PRE_COMPACTION_DEFAULT_CONFIG}
            elif planned.path == root / "norms" / "README.md":
                known_previous = {LEGACY_NORMS_README}
            elif planned.path == root / "norms" / "INDEX.md":
                known_previous = {LEGACY_NORMS_INDEX}
            elif planned.path == root / "AGENTS.md":
                known_previous = {alternate_agents}
            if known_previous:
                try:
                    existing = planned.path.read_text(encoding="utf-8")
                except OSError as error:
                    message = f"cannot read existing generated file: {planned.path}: {error}"
                    raise ValueError(message) from error
                if existing in known_previous:
                    created.append(planned.path)
                    if not dry_run:
                        planned.path.write_text(planned.content, encoding="utf-8")
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


def _state_gitignore() -> str:
    return """managed-state.json
local-install.json
docs/
evals/
cache/
runs/
"""
