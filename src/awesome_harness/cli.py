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
from awesome_harness.config import HarnessConfigError, load_config
from awesome_harness.local_install import (
    LocalInstallError,
    disable_local_install,
    enable_local_install,
    git_context,
    is_local_install,
    private_directories_absent,
    record_managed_paths,
)
from awesome_harness.managed import ManagedStateError, apply, plan, status
from awesome_harness.norms import (
    NormValidationError,
    ScopeContext,
    build_norm_index,
    norm_manifest,
    render_norm_bundle,
)
from awesome_harness.runtime import inspect_opencode
from awesome_harness.validate import validate_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Initialize, inspect, and evaluate development-agent harnesses.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="install the portable project baseline")
    init_parser.add_argument("path", nargs="?", default=".")
    init_parser.add_argument("--dry-run", action="store_true")
    visibility = init_parser.add_mutually_exclusive_group()
    visibility.add_argument(
        "--local",
        action="store_true",
        dest="local_install",
        default=True,
        help="keep harness control files clone-local (default)",
    )
    visibility.add_argument(
        "--tracked",
        action="store_false",
        dest="local_install",
        help="leave initialized files visible to Git for project use",
    )
    init_parser.add_argument(
        "--apply",
        action="store_true",
        dest="apply_now",
        help="apply generated runtime projections after initialization",
    )

    plan_parser = subparsers.add_parser("plan", help="preview managed runtime projections")
    plan_parser.add_argument("path", nargs="?", default=".")
    plan_parser.add_argument("--json", action="store_true", dest="as_json")

    apply_parser = subparsers.add_parser("apply", help="apply managed runtime projections")
    apply_parser.add_argument("path", nargs="?", default=".")

    status_parser = subparsers.add_parser("status", help="show managed projection status")
    status_parser.add_argument("path", nargs="?", default=".")
    status_parser.add_argument("--json", action="store_true", dest="as_json")

    norms_parser = subparsers.add_parser("norms", help="validate and resolve coding norms")
    norms_subparsers = norms_parser.add_subparsers(dest="norms_command", required=True)
    norms_validate = norms_subparsers.add_parser("validate", help="validate a norm library")
    norms_validate.add_argument("root", nargs="?", default=".")
    norms_validate.add_argument("--json", action="store_true", dest="as_json")
    norms_resolve = norms_subparsers.add_parser("resolve", help="resolve norms for a task scope")
    norms_resolve.add_argument("root", nargs="?", default=".")
    norms_resolve.add_argument("--area")
    norms_resolve.add_argument("--language")
    norms_resolve.add_argument("--path")
    norms_resolve.add_argument("--task")
    norms_resolve.add_argument("--include-drafts", action="store_true")
    norms_resolve.add_argument("--include-on-demand", action="store_true")
    norms_resolve.add_argument("--json", action="store_true", dest="as_json")

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
        return _run_init(
            Path(args.path),
            dry_run=args.dry_run,
            apply_now=args.apply_now,
            local_install=args.local_install,
        )
    if args.command == "plan":
        return _run_projection_command("plan", Path(args.path), as_json=args.as_json)
    if args.command == "apply":
        return _run_apply(Path(args.path))
    if args.command == "status":
        return _run_projection_command("status", Path(args.path), as_json=args.as_json)
    if args.command == "norms":
        return _run_norms(args)
    if args.command == "validate":
        return _run_validate(Path(args.path), as_json=args.as_json)
    if args.command == "doctor":
        return _run_doctor(as_json=args.as_json)
    if args.command == "eval":
        print("Eval runner scaffolded. See evals/README.md and evals/cases/smoke.json.")
        return 0
    return 2


def _run_init(
    path: Path, *, dry_run: bool, apply_now: bool, local_install: bool
) -> int:
    if dry_run and apply_now:
        print("error: --dry-run and --apply cannot be combined", file=sys.stderr)
        return 2
    root = path.resolve()
    try:
        whole_directories = private_directories_absent(root)
        if local_install:
            git_context(root)
        created = initialize(
            root,
            dry_run=dry_run,
            private_scaffold=local_install,
        )
        if not dry_run:
            if local_install:
                enable_local_install(root, created, whole_directories)
            else:
                disable_local_install(root)
    except (ValueError, LocalInstallError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    verb = "Would initialize" if dry_run else "Initialized"
    if not created:
        print("Harness metadata already initialized; no files changed.")
    else:
        for created_path in created:
            print(f"{verb}: {created_path}")
    return _run_apply(root) if apply_now else 0


def _run_projection_command(command: str, path: Path, *, as_json: bool) -> int:
    try:
        root = path.resolve()
        changes = plan(root) if command == "plan" else status(root)
    except (HarnessConfigError, ManagedStateError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps([change.as_dict(root) for change in changes], indent=2))
    else:
        for change in changes:
            relative = change.path.relative_to(root)
            print(f"{change.action.upper():8} {relative}: {change.reason}")
    return 1 if any(change.action == "conflict" for change in changes) else 0


def _run_apply(path: Path) -> int:
    try:
        root = path.resolve()
        if is_local_install(root):
            git_context(root)
        result = apply(root)
        record_managed_paths(root, result.written)
    except (HarnessConfigError, LocalInstallError, ManagedStateError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if not result.written:
        print("Managed runtime projections already match desired state.")
        return 0
    for written in result.written:
        print(f"Applied: {written.relative_to(root)}")
    return 0


def _run_norms(args: argparse.Namespace) -> int:
    try:
        config = load_config(Path(args.root))
        index = build_norm_index(config.norms.source)
        if args.norms_command == "validate":
            if args.as_json:
                print(json.dumps({"source": str(config.norms.source), "count": len(index.norms)}))
            else:
                print(f"Validated {len(index.norms)} norms from {config.norms.source}")
            return 0
        include_drafts = bool(args.include_drafts or config.norms.include_drafts)
        resolved = index.resolve(
            ScopeContext(
                area=args.area,
                language=args.language,
                path=args.path,
                task=args.task,
            ),
            include_drafts=include_drafts,
            include_on_demand=args.include_on_demand,
        )
        if args.as_json:
            print(json.dumps(norm_manifest(resolved), indent=2))
        else:
            print(render_norm_bundle(resolved), end="")
        return 0
    except (HarnessConfigError, NormValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


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
        "opencode": inspect_opencode().as_dict(),
    }
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        for key, value in report.items():
            print(f"{key}: {value or 'not found'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
