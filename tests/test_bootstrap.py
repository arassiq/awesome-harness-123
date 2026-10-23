from pathlib import Path

from awesome_harness.bootstrap import initialize


def test_initialize_creates_expected_files(tmp_path: Path) -> None:
    created = initialize(tmp_path)

    assert created == (
        tmp_path / "harness.toml",
        tmp_path / ".harness" / "README.md",
    )
    assert (tmp_path / "harness.toml").is_file()
    assert (tmp_path / ".harness" / "README.md").is_file()


def test_initialize_does_not_overwrite_existing_config(tmp_path: Path) -> None:
    config = tmp_path / "harness.toml"
    config.write_text("custom = true\n", encoding="utf-8")

    initialize(tmp_path)

    assert config.read_text(encoding="utf-8") == "custom = true\n"


def test_dry_run_reports_without_writing(tmp_path: Path) -> None:
    created = initialize(tmp_path, dry_run=True)

    assert len(created) == 2
    assert not (tmp_path / "harness.toml").exists()
