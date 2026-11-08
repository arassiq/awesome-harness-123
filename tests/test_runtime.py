from __future__ import annotations

import subprocess

from awesome_harness.runtime import OPENCODE, inspect_opencode


def test_inspect_opencode_matches_pin(monkeypatch: object) -> None:
    monkeypatch.setattr("awesome_harness.runtime.shutil.which", lambda _: "/bin/opencode")  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "awesome_harness.runtime.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], returncode=0, stdout=f"opencode v{OPENCODE.version}\n", stderr=""
        ),
    )

    status = inspect_opencode()

    assert status.status == "match"
    assert status.detected_version == OPENCODE.version


def test_inspect_opencode_rejects_broken_wrapper(monkeypatch: object) -> None:
    monkeypatch.setattr("awesome_harness.runtime.shutil.which", lambda _: "/bin/opencode")  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "awesome_harness.runtime.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], returncode=127, stdout="", stderr="real opencode binary not found"
        ),
    )

    status = inspect_opencode()

    assert status.status == "unavailable"
    assert status.detected_version is None
