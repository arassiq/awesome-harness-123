import subprocess
from pathlib import Path

from awesome_harness.cli import main


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_doctor_json(capsys: object) -> None:
    assert main(["doctor", "--json"]) == 0


def test_init_rejects_missing_directory(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path / "missing")]) == 2


def test_init_apply_installs_managed_opencode_plugin(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["init", str(tmp_path), "--apply"]) == 0

    assert (tmp_path / "harness.toml").is_file()
    assert (tmp_path / "norms" / "README.md").is_file()
    assert (tmp_path / ".harness/docs/INDEX.md").is_file()
    assert (tmp_path / ".harness/evals/README.md").is_file()
    assert not (tmp_path / "docs").exists()
    assert "`.harness/docs/INDEX.md`" in (tmp_path / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert (tmp_path / ".opencode/plugins/awesome-harness/index.ts").is_file()
    assert main(["status", str(tmp_path)]) == 0
    exclude = (tmp_path / ".git/info/exclude").read_text(encoding="utf-8")
    assert "/AGENTS.md" in exclude
    assert "/norms/" in exclude
    assert "/.harness/" in exclude
    assert "/.opencode/plugins/awesome-harness/" in exclude
    assert "/docs/" not in exclude
    assert "/evals/" not in exclude
    status = subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--short"],
        capture_output=True,
        check=True,
        text=True,
    )
    assert status.stdout == ""


def test_norms_validate_shared_initialized_library(tmp_path: Path, capsys: object) -> None:
    _git_init(tmp_path)
    assert main(["init", str(tmp_path)]) == 0

    assert main(["norms", "validate", str(tmp_path)]) == 0
    assert "Validated 3 norms" in capsys.readouterr().out  # type: ignore[attr-defined]


def test_default_local_init_requires_git(tmp_path: Path, capsys: object) -> None:
    assert main(["init", str(tmp_path)]) == 2

    assert "git init" in capsys.readouterr().err  # type: ignore[attr-defined]
    assert not (tmp_path / "harness.toml").exists()


def test_tracked_init_works_without_git_and_leaves_files_visible(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path), "--tracked"]) == 0

    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "docs/INDEX.md").is_file()
    assert (tmp_path / "evals/README.md").is_file()
    assert not (tmp_path / ".harness/local-install.json").exists()


def test_tracked_init_removes_only_managed_local_exclude_block(tmp_path: Path) -> None:
    _git_init(tmp_path)
    exclude = tmp_path / ".git/info/exclude"
    exclude.write_text("*.personal\n", encoding="utf-8")
    assert main(["init", str(tmp_path)]) == 0

    assert main(["init", str(tmp_path), "--tracked"]) == 0

    rendered = exclude.read_text(encoding="utf-8")
    assert rendered == "*.personal\n"
    assert not (tmp_path / ".harness/local-install.json").exists()
    assert "`docs/INDEX.md`" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert (tmp_path / "docs/INDEX.md").is_file()


def test_local_init_does_not_hide_preexisting_user_files(tmp_path: Path) -> None:
    _git_init(tmp_path)
    agents = tmp_path / "AGENTS.md"
    private_norm = tmp_path / "norms/private.md"
    private_norm.parent.mkdir()
    agents.write_text("# Existing project instructions\n", encoding="utf-8")
    private_norm.write_text("existing user file\n", encoding="utf-8")

    assert main(["init", str(tmp_path)]) == 0

    exclude = (tmp_path / ".git/info/exclude").read_text(encoding="utf-8")
    assert "/AGENTS.md" not in exclude
    assert "/norms/" not in exclude.splitlines()
    assert "/norms/INDEX.md" in exclude
    assert agents.read_text(encoding="utf-8") == "# Existing project instructions\n"
    check = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "AGENTS.md", "norms/private.md"],
        capture_output=True,
        check=False,
        text=True,
    )
    assert check.returncode == 1
    assert check.stdout == ""


def test_validate_current_repository() -> None:
    assert main(["validate", "."]) == 0
