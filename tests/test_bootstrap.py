from pathlib import Path

from awesome_harness.bootstrap import (
    LEGACY_DEFAULT_CONFIG,
    LEGACY_NORMS_INDEX,
    PRE_COMPACTION_DEFAULT_CONFIG,
    initialize,
)


def test_initialize_creates_expected_files(tmp_path: Path) -> None:
    created = initialize(tmp_path)

    assert created[0:3] == (
        tmp_path / "harness.toml",
        tmp_path / ".harness" / "README.md",
        tmp_path / ".harness" / ".gitignore",
    )
    assert (tmp_path / "harness.toml").is_file()
    assert (tmp_path / ".harness" / "README.md").is_file()
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "docs" / "INDEX.md").is_file()
    assert (tmp_path / "docs" / "design" / "README.md").is_file()
    assert (tmp_path / "evals" / "README.md").is_file()
    assert (tmp_path / "norms" / "INDEX.md").is_file()
    assert (tmp_path / "norms" / "backend" / "python" / "api-design.md").is_file()


def test_initialize_does_not_overwrite_existing_config(tmp_path: Path) -> None:
    config = tmp_path / "harness.toml"
    config.write_text("custom = true\n", encoding="utf-8")

    initialize(tmp_path)

    assert config.read_text(encoding="utf-8") == "custom = true\n"


def test_dry_run_reports_without_writing(tmp_path: Path) -> None:
    created = initialize(tmp_path, dry_run=True)

    assert len(created) > 5
    assert not (tmp_path / "harness.toml").exists()


def test_initialize_migrates_only_exact_legacy_generated_config(tmp_path: Path) -> None:
    config = tmp_path / "harness.toml"
    config.write_text(LEGACY_DEFAULT_CONFIG, encoding="utf-8")

    initialized = initialize(tmp_path)

    assert config in initialized
    assert "[runtimes.opencode]" in config.read_text(encoding="utf-8")
    assert "[norms]" in config.read_text(encoding="utf-8")


def test_initialize_migrates_exact_pre_compaction_config(tmp_path: Path) -> None:
    config = tmp_path / "harness.toml"
    config.write_text(PRE_COMPACTION_DEFAULT_CONFIG, encoding="utf-8")

    initialized = initialize(tmp_path)

    assert config in initialized
    assert "[compaction]" in config.read_text(encoding="utf-8")


def test_initialize_preserves_existing_agent_instructions_and_norms(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    norm = tmp_path / "norms/backend/python/api-design.md"
    norm.parent.mkdir(parents=True)
    agents.write_text("# Project-owned instructions\n", encoding="utf-8")
    norm.write_text("project-owned norm\n", encoding="utf-8")

    initialize(tmp_path)

    assert agents.read_text(encoding="utf-8") == "# Project-owned instructions\n"
    assert norm.read_text(encoding="utf-8") == "project-owned norm\n"


def test_initialize_upgrades_exact_empty_generated_norm_index(tmp_path: Path) -> None:
    index = tmp_path / "norms/INDEX.md"
    index.parent.mkdir(parents=True)
    index.write_text(LEGACY_NORMS_INDEX, encoding="utf-8")

    initialized = initialize(tmp_path)

    assert index in initialized
    assert "backend.python.api_design" in index.read_text(encoding="utf-8")


def test_repeated_initialization_is_idempotent(tmp_path: Path) -> None:
    initialize(tmp_path)

    assert initialize(tmp_path) == ()
