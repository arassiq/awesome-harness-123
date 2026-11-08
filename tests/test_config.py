from pathlib import Path

import pytest

from awesome_harness.bootstrap import (
    LEGACY_DEFAULT_CONFIG,
    PRE_COMPACTION_DEFAULT_CONFIG,
    initialize,
)
from awesome_harness.config import HarnessConfigError, load_config


def test_load_initialized_config(tmp_path: Path) -> None:
    initialize(tmp_path)

    config = load_config(tmp_path)

    assert config.opencode.enabled
    assert config.opencode.version == "2.2.1"
    assert config.norms.source == tmp_path / "norms"
    assert not config.norms.include_drafts
    assert not config.compaction.enabled
    assert config.compaction.strategy == "cliff"
    assert config.compaction.trigger_percent == 60
    assert config.compaction.recent_turn_pairs == 8


def test_config_rejects_norm_source_outside_repository(tmp_path: Path) -> None:
    initialize(tmp_path)
    path = tmp_path / "harness.toml"
    path.write_text(path.read_text().replace('source = "norms"', 'source = "../private"'))

    with pytest.raises(HarnessConfigError, match="repository-relative"):
        load_config(tmp_path)


def test_config_directs_legacy_generated_config_to_init_migration(tmp_path: Path) -> None:
    (tmp_path / "harness.toml").write_text(LEGACY_DEFAULT_CONFIG, encoding="utf-8")

    with pytest.raises(HarnessConfigError, match="harness init"):
        load_config(tmp_path)


def test_config_directs_pre_compaction_config_to_init_migration(tmp_path: Path) -> None:
    (tmp_path / "harness.toml").write_text(
        PRE_COMPACTION_DEFAULT_CONFIG, encoding="utf-8"
    )

    with pytest.raises(HarnessConfigError, match="harness init"):
        load_config(tmp_path)
