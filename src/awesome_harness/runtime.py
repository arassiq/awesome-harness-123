"""Runtime version pins and local inspection."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RuntimePin:
    name: str
    version: str
    install_command: str


@dataclass(frozen=True)
class RuntimeStatus:
    path: str | None
    detected_version: str | None
    expected_version: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


OPENCODE = RuntimePin(
    name="opencode",
    version="2.2.1",
    install_command="npm install --global @opencode/cli@2.2.1",
)


def inspect_opencode() -> RuntimeStatus:
    """Inspect the executable, not merely a wrapper present on PATH."""
    path = shutil.which(OPENCODE.name)
    if path is None:
        return RuntimeStatus(
            path=None,
            detected_version=None,
            expected_version=OPENCODE.version,
            status="missing",
            detail=f"Install with: {OPENCODE.install_command}",
        )

    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return RuntimeStatus(
            path=path,
            detected_version=None,
            expected_version=OPENCODE.version,
            status="unavailable",
            detail=str(error),
        )

    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    match = re.search(r"\bopencode\s+v?([^\s]+)", output, re.IGNORECASE)
    if result.returncode != 0 or match is None:
        return RuntimeStatus(
            path=path,
            detected_version=None,
            expected_version=OPENCODE.version,
            status="unavailable",
            detail=output or f"version command exited {result.returncode}",
        )

    detected = match.group(1)
    matches_pin = detected == OPENCODE.version
    return RuntimeStatus(
        path=path,
        detected_version=detected,
        expected_version=OPENCODE.version,
        status="match" if matches_pin else "mismatch",
        detail="runtime matches the harness pin" if matches_pin else "runtime differs from the pin",
    )
