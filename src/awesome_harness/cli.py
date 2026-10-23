"""Command-line interface for awesome-harness-123."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from awesome_harness import __version__
from awesome_harness.bootstrap import initialize
from awesome_harness.validate import validate_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Initialize, inspect, and evaluate development-agent harnesses.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize harness metadata")
    init_parser.add_argument("path", nargs="?", default=".")
    init_parser.add_argument("--dry-run", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="validate repository structure")
    validate_parser.add_argument("path", nargs="?", default=".")
    validate_parser.add_argument("--json", action="store_true", dest="as_json")

    doctor_parser = subparsers.add_parser("doctor", help="inspect local prerequisites")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")

    subparsers.add_parser("eval", help="show the current evaluation scaffold")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return _run_init(Path(args.path), dry_run=args.dry_run)
    if args.command == "validate":
        return _run_validate(Path(args.path), as_json=args.as_json)
    if args.command == "doctor":
        return _run_doctor(as_json=args.as_json)
    if args.command == "eval":
        print("Eval runner scaffolded. See evals/README.md and evals/cases/smoke.json.")
        return 0
    return 2


def _run_init(path: Path, *, dry_run: bool) -> int:
    try:
        created = initialize(path, dry_run=dry_run)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    verb = "Would create" if dry_run else "Created"
    if not created:
        print("Harness metadata already initialized; no files changed.")
        return 0
    for created_path in created:
        print(f"{verb}: {created_path}")
    return 0


def _run_validate(path: Path, *, as_json: bool) -> int:
    checks = validate_repository(path)
    if as_json:
        print(json.dumps([check.__dict__ for check in checks], indent=2))
    else:
        for check in checks:
            marker = "PASS" if check.ok else "FAIL"
            print(f"[{marker}] {check.name}: {check.detail}")
    return 0 if all(check.ok for check in checks) else 1


def _run_doctor(*, as_json: bool) -> int:
    report = {
        "harness_version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git": shutil.which("git"),
        "uv": shutil.which("uv"),
        "opencode": shutil.which("opencode"),
    }
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        for key, value in report.items():
            print(f"{key}: {value or 'not found'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
