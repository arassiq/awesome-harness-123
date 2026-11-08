from pathlib import Path

import pytest

from awesome_harness.bootstrap import initialize
from awesome_harness.managed import ManagedStateError, apply, plan


def test_apply_creates_owned_opencode_projection(tmp_path: Path) -> None:
    initialize(tmp_path)

    result = apply(tmp_path)

    plugin = tmp_path / ".opencode/plugins/awesome-harness/index.ts"
    assert result.written == (plugin,)
    assert plugin.is_file()
    assert plan(tmp_path)[0].action == "noop"


def test_apply_refuses_unowned_existing_projection(tmp_path: Path) -> None:
    initialize(tmp_path)
    plugin = tmp_path / ".opencode/plugins/awesome-harness/index.ts"
    plugin.parent.mkdir(parents=True)
    plugin.write_text("// user file\n")

    assert plan(tmp_path)[0].action == "conflict"
    with pytest.raises(ManagedStateError, match="user-owned"):
        apply(tmp_path)
    assert plugin.read_text() == "// user file\n"


def test_apply_detects_edits_to_owned_projection(tmp_path: Path) -> None:
    initialize(tmp_path)
    apply(tmp_path)
    plugin = tmp_path / ".opencode/plugins/awesome-harness/index.ts"
    plugin.write_text(plugin.read_text() + "// local edit\n")

    assert plan(tmp_path)[0].action == "conflict"


def test_disabling_opencode_removes_only_unchanged_owned_projection(tmp_path: Path) -> None:
    initialize(tmp_path)
    apply(tmp_path)
    config = tmp_path / "harness.toml"
    config.write_text(config.read_text().replace("enabled = true", "enabled = false", 1))

    assert plan(tmp_path)[0].action == "delete"
    apply(tmp_path)

    assert not (tmp_path / ".opencode/plugins/awesome-harness/index.ts").exists()
