"""Parse the repository-owned desired state in ``harness.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from awesome_harness.bootstrap import LEGACY_DEFAULT_CONFIG, PRE_COMPACTION_DEFAULT_CONFIG


class HarnessConfigError(ValueError):
    """The desired-state file is missing or invalid."""


@dataclass(frozen=True)
class OpenCodeConfig:
    enabled: bool
    version: str


@dataclass(frozen=True)
class NormsConfig:
    enabled: bool
    source: Path
    include_drafts: bool


@dataclass(frozen=True)
class CompactionConfig:
    enabled: bool
    strategy: str
    trigger_percent: int
    recent_turn_pairs: int
    tool_result_max_chars: int
    tool_signature_max_chars: int
    reasoning_max_chars: int


@dataclass(frozen=True)
class HarnessConfig:
    version: int
    profile: str
    opencode: OpenCodeConfig
    norms: NormsConfig
    compaction: CompactionConfig


def load_config(root: Path) -> HarnessConfig:
    """Load and strictly validate ``harness.toml`` beneath *root*."""
    root = root.resolve()
    path = root / "harness.toml"
    try:
        text = path.read_text(encoding="utf-8")
        if text in {LEGACY_DEFAULT_CONFIG, PRE_COMPACTION_DEFAULT_CONFIG}:
            raise HarnessConfigError(
                f"legacy generated config detected at {path}; run `harness init` to migrate it"
            )
        raw = tomllib.loads(text)
    except FileNotFoundError as error:
        raise HarnessConfigError(f"missing desired-state file: {path}") from error
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise HarnessConfigError(f"cannot parse {path}: {error}") from error

    _require_keys(raw, {"version", "profile", "runtimes", "norms", "compaction"}, "top level")
    version = _integer(raw, "version", "top level")
    if version != 1:
        raise HarnessConfigError("version must be 1")
    profile = _string(raw, "profile", "top level")

    runtimes = _table(raw, "runtimes", "top level")
    _require_keys(runtimes, {"opencode"}, "runtimes")
    opencode_raw = _table(runtimes, "opencode", "runtimes")
    _require_keys(opencode_raw, {"enabled", "version"}, "runtimes.opencode")
    opencode = OpenCodeConfig(
        enabled=_boolean(opencode_raw, "enabled", "runtimes.opencode"),
        version=_string(opencode_raw, "version", "runtimes.opencode"),
    )

    norms_raw = _table(raw, "norms", "top level")
    _require_keys(norms_raw, {"enabled", "source", "include_drafts"}, "norms")
    source_text = _string(norms_raw, "source", "norms")
    source = Path(source_text)
    if source.is_absolute() or ".." in source.parts:
        raise HarnessConfigError("norms.source must be a repository-relative path without '..'")
    norms = NormsConfig(
        enabled=_boolean(norms_raw, "enabled", "norms"),
        source=root / source,
        include_drafts=_boolean(norms_raw, "include_drafts", "norms"),
    )

    compaction_raw = _table(raw, "compaction", "top level")
    _require_keys(
        compaction_raw,
        {
            "enabled",
            "strategy",
            "trigger_percent",
            "recent_turn_pairs",
            "tool_result_max_chars",
            "tool_signature_max_chars",
            "reasoning_max_chars",
        },
        "compaction",
    )
    strategy = _string(compaction_raw, "strategy", "compaction")
    if strategy != "cliff":
        raise HarnessConfigError("compaction.strategy must be 'cliff'")
    trigger_percent = _integer(compaction_raw, "trigger_percent", "compaction")
    if not 1 <= trigger_percent <= 99:
        raise HarnessConfigError("compaction.trigger_percent must be between 1 and 99")
    compaction = CompactionConfig(
        enabled=_boolean(compaction_raw, "enabled", "compaction"),
        strategy=strategy,
        trigger_percent=trigger_percent,
        recent_turn_pairs=_non_negative_integer(
            compaction_raw, "recent_turn_pairs", "compaction"
        ),
        tool_result_max_chars=_non_negative_integer(
            compaction_raw, "tool_result_max_chars", "compaction"
        ),
        tool_signature_max_chars=_non_negative_integer(
            compaction_raw, "tool_signature_max_chars", "compaction"
        ),
        reasoning_max_chars=_non_negative_integer(
            compaction_raw, "reasoning_max_chars", "compaction"
        ),
    )
    return HarnessConfig(
        version=version,
        profile=profile,
        opencode=opencode,
        norms=norms,
        compaction=compaction,
    )


def _require_keys(table: dict[str, object], expected: set[str], label: str) -> None:
    unknown = set(table) - expected
    missing = expected - set(table)
    if unknown:
        raise HarnessConfigError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
    if missing:
        raise HarnessConfigError(f"{label} is missing fields: {', '.join(sorted(missing))}")


def _table(table: dict[str, object], key: str, label: str) -> dict[str, object]:
    value = table.get(key)
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value):
        raise HarnessConfigError(f"{label}.{key} must be a table")
    return cast("dict[str, object]", value)


def _string(table: dict[str, object], key: str, label: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HarnessConfigError(f"{label}.{key} must be a non-empty string")
    return value


def _boolean(table: dict[str, object], key: str, label: str) -> bool:
    value = table.get(key)
    if not isinstance(value, bool):
        raise HarnessConfigError(f"{label}.{key} must be a boolean")
    return value


def _integer(table: dict[str, object], key: str, label: str) -> int:
    value = table.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise HarnessConfigError(f"{label}.{key} must be an integer")
    return value


def _non_negative_integer(table: dict[str, object], key: str, label: str) -> int:
    value = _integer(table, key, label)
    if value < 0:
        raise HarnessConfigError(f"{label}.{key} must be non-negative")
    return value
