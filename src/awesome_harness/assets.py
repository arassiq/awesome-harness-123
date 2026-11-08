"""Read the portable baseline bundled with the installed harness."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path


@dataclass(frozen=True)
class BaselineAsset:
    """One UTF-8 file installed into a target repository."""

    destination: Path
    content: str


def baseline_assets(*, private_scaffold: bool = False) -> tuple[BaselineAsset, ...]:
    """Return the generic project scaffold and shared norm library.

    Local installations place documentation and evaluations beneath ``.harness`` so the target's
    ordinary project namespaces remain untouched and commit-ready.
    """
    scaffold = _asset_tree("bundled_scaffold", "scaffold", Path())
    if private_scaffold:
        scaffold = tuple(_private_scaffold_asset(asset) for asset in scaffold)
    norms = _asset_tree("bundled_norms", "norms", Path("norms"))
    return scaffold + norms


def _private_scaffold_asset(asset: BaselineAsset) -> BaselineAsset:
    destination = asset.destination
    content = asset.content
    if destination.parts and destination.parts[0] in {"docs", "evals"}:
        destination = Path(".harness") / destination
    if destination == Path("AGENTS.md"):
        content = content.replace("`docs/INDEX.md`", "`.harness/docs/INDEX.md`")
    return BaselineAsset(destination=destination, content=content)


def _asset_tree(
    package_name: str, repository_name: str, destination_root: Path
) -> tuple[BaselineAsset, ...]:
    package_root = files("awesome_harness").joinpath(package_name)
    if package_root.is_dir():
        return _read_tree(package_root, destination_root)

    repository_root = Path(__file__).resolve().parents[2] / repository_name
    if not repository_root.is_dir():
        raise ValueError(
            f"harness installation is missing bundled baseline assets: {package_name}"
        )
    return _read_tree(repository_root, destination_root)


def _read_tree(root: Traversable, destination_root: Path) -> tuple[BaselineAsset, ...]:
    assets: list[BaselineAsset] = []

    def visit(current: Traversable, relative: Path) -> None:
        for child in sorted(current.iterdir(), key=lambda item: item.name):
            child_relative = relative / child.name
            if child.is_dir():
                visit(child, child_relative)
            elif child.is_file():
                assets.append(
                    BaselineAsset(
                        destination=destination_root / child_relative,
                        content=child.read_text(encoding="utf-8"),
                    )
                )

    visit(root, Path())
    return tuple(assets)
