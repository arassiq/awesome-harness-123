from pathlib import Path

from awesome_harness.cli import main


def test_doctor_json(capsys: object) -> None:
    assert main(["doctor", "--json"]) == 0


def test_init_rejects_missing_directory(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path / "missing")]) == 2


def test_validate_current_repository() -> None:
    assert main(["validate", "."]) == 0
