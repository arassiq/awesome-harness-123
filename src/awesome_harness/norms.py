"""Deterministic loader and index for proposed Markdown coding norms."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Literal, NoReturn, TypeVar, cast

NormStatus = Literal["draft", "active", "deprecated"]
NormPriority = Literal["required", "advisory"]
NormDelivery = Literal["always", "scoped", "on_demand"]
RelationType = Literal["requires", "conflicts", "supersedes", "example_of", "related_to"]
ProvenanceKind = Literal["repository", "upstream", "personal", "external"]
Value = TypeVar("Value", bound=str)

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SELECTOR_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
_TOP_LEVEL_KEYS = {
    "schema_version",
    "id",
    "version",
    "title",
    "summary",
    "status",
    "priority",
    "delivery",
    "scope",
    "relations",
    "provenance",
}
_SECTION_ORDER = ("Rule", "Rationale", "Examples", "Failure modes")
_REQUIRED_SECTIONS = frozenset({"Rule", "Rationale"})
_SECTION_LIMITS = {
    "Rule": 2_000,
    "Rationale": 3_000,
    "Examples": 4_000,
    "Failure modes": 2_000,
}
_MAX_FRONTMATTER_CHARS = 8_000
_MAX_BODY_CHARS = 8_000


class NormValidationError(ValueError):
    """A norm file or library violates the proposed contract."""


@dataclass(frozen=True)
class NormScope:
    """Deterministic selectors for deciding whether a norm applies."""

    areas: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    tasks: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.areas or self.languages or self.paths or self.tasks)

    def matches(self, context: ScopeContext) -> bool:
        """Return true when every populated selector dimension matches the context."""
        return (
            _matches_value(self.areas, context.area)
            and _matches_value(self.languages, context.language)
            and _matches_path(self.paths, context.path)
            and _matches_value(self.tasks, context.task)
        )


@dataclass(frozen=True)
class ScopeContext:
    """Known task attributes used by deterministic norm resolution."""

    area: str | None = None
    language: str | None = None
    path: str | None = None
    task: str | None = None


@dataclass(frozen=True, order=True)
class NormRelation:
    type: RelationType
    target: str


@dataclass(frozen=True)
class NormProvenance:
    kind: ProvenanceKind
    source: str
    owner: str | None = None
    reviewed_at: date | None = None


@dataclass(frozen=True)
class NormSection:
    name: str
    content: str


@dataclass(frozen=True)
class Norm:
    """One validated runtime-neutral coding norm."""

    schema_version: int
    id: str
    version: int
    title: str
    summary: str
    status: NormStatus
    priority: NormPriority
    delivery: NormDelivery
    scope: NormScope
    relations: tuple[NormRelation, ...]
    provenance: NormProvenance
    sections: tuple[NormSection, ...]
    source_path: Path


@dataclass(frozen=True)
class NormIndex:
    """Validated norm collection ordered by stable norm ID."""

    norms: tuple[Norm, ...]

    def resolve(
        self,
        context: ScopeContext,
        *,
        include_drafts: bool = False,
        include_deprecated: bool = False,
        include_on_demand: bool = False,
    ) -> tuple[Norm, ...]:
        """Resolve applicable norms and their transitive ``requires`` relations."""
        by_id = {norm.id: norm for norm in self.norms}
        selected: set[str] = set()

        for norm in self.norms:
            if not _status_is_enabled(norm, include_drafts, include_deprecated):
                continue
            scope_matches = norm.scope.matches(context)
            should_include = (
                norm.delivery == "always"
                or (norm.delivery == "scoped" and scope_matches)
                or (norm.delivery == "on_demand" and include_on_demand and scope_matches)
            )
            if should_include:
                selected.add(norm.id)

        pending = list(selected)
        while pending:
            norm = by_id[pending.pop()]
            for relation in norm.relations:
                if relation.type == "requires" and relation.target not in selected:
                    selected.add(relation.target)
                    pending.append(relation.target)

        return tuple(by_id[norm_id] for norm_id in sorted(selected))


def render_norm_bundle(norms: Sequence[Norm]) -> str:
    """Render selected norms without frontmatter in a cache-stable order."""
    ordered = sorted(norms, key=lambda norm: norm.id)
    if not ordered:
        return "No active coding norms matched this scope."
    blocks = ["# Resolved coding norms"]
    for norm in ordered:
        blocks.append(
            "\n".join(
                [
                    f"## {norm.id} (v{norm.version}, {norm.priority})",
                    *(
                        f"### {section.name}\n\n{section.content}"
                        for section in norm.sections
                    ),
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def norm_manifest(norms: Sequence[Norm]) -> list[dict[str, object]]:
    """Return a bounded structured view suitable for CLI and adapter output."""
    return [
        {
            "id": norm.id,
            "version": norm.version,
            "title": norm.title,
            "summary": norm.summary,
            "priority": norm.priority,
            "delivery": norm.delivery,
            "sections": [
                {"name": section.name, "content": section.content} for section in norm.sections
            ],
        }
        for norm in sorted(norms, key=lambda item: item.id)
    ]


def load_norm(path: Path) -> Norm:
    """Load and validate one Markdown norm with TOML frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise NormValidationError(f"{path}: cannot read norm: {error}") from error

    frontmatter, body = _split_frontmatter(path, text)
    try:
        parsed: object = tomllib.loads(frontmatter)
    except tomllib.TOMLDecodeError as error:
        raise NormValidationError(f"{path}: invalid TOML frontmatter: {error}") from error

    metadata = _mapping(parsed, path, "frontmatter")
    unknown_keys = set(metadata) - _TOP_LEVEL_KEYS
    missing_keys = _TOP_LEVEL_KEYS - set(metadata)
    if unknown_keys:
        _raise(path, f"unknown frontmatter fields: {', '.join(sorted(unknown_keys))}")
    if missing_keys:
        _raise(path, f"missing frontmatter fields: {', '.join(sorted(missing_keys))}")

    schema_version = _integer(metadata, "schema_version", path)
    if schema_version != 1:
        _raise(path, "schema_version must be 1")
    norm_id = _bounded_string(metadata, "id", path, 120)
    if not _ID_PATTERN.fullmatch(norm_id):
        _raise(path, f"invalid norm id: {norm_id!r}")
    version = _integer(metadata, "version", path)
    if version < 1:
        _raise(path, "version must be at least 1")

    title = _bounded_string(metadata, "title", path, 100)
    summary = _bounded_string(metadata, "summary", path, 240)
    status: NormStatus = _literal(metadata, "status", path, ("draft", "active", "deprecated"))
    priority: NormPriority = _literal(metadata, "priority", path, ("required", "advisory"))
    delivery: NormDelivery = _literal(
        metadata, "delivery", path, ("always", "scoped", "on_demand")
    )
    scope = _parse_scope(_mapping(metadata["scope"], path, "scope"), path)
    relations = _parse_relations(metadata["relations"], path, norm_id)
    provenance = _parse_provenance(_mapping(metadata["provenance"], path, "provenance"), path)
    sections = _parse_sections(path, body)

    if delivery == "always" and priority != "required":
        _raise(path, "an always-delivered norm must have required priority")
    if delivery == "always" and not scope.is_empty:
        _raise(path, "an always-delivered norm must have an empty scope")
    if delivery == "scoped" and scope.is_empty:
        _raise(path, "a scoped norm must define at least one selector")

    return Norm(
        schema_version=schema_version,
        id=norm_id,
        version=version,
        title=title,
        summary=summary,
        status=status,
        priority=priority,
        delivery=delivery,
        scope=scope,
        relations=relations,
        provenance=provenance,
        sections=sections,
        source_path=path,
    )


def build_norm_index(root: Path) -> NormIndex:
    """Load a norm tree, validate cross-file integrity, and return stable ordering."""
    candidates = sorted(root.rglob("*.md"))
    norm_paths = [path for path in candidates if path.name not in {"INDEX.md", "README.md"}]
    norms = tuple(sorted((load_norm(path) for path in norm_paths), key=lambda norm: norm.id))

    by_id: dict[str, Norm] = {}
    for norm in norms:
        previous = by_id.get(norm.id)
        if previous is not None:
            raise NormValidationError(
                f"duplicate norm id {norm.id!r}: {previous.source_path} and {norm.source_path}"
            )
        by_id[norm.id] = norm

    for norm in norms:
        for relation in norm.relations:
            target = by_id.get(relation.target)
            if target is None:
                raise NormValidationError(
                    f"{norm.source_path}: relation target {relation.target!r} does not exist"
                )
            active_requirement_is_invalid = (
                relation.type == "requires"
                and norm.status == "active"
                and target.status != "active"
            )
            if active_requirement_is_invalid:
                raise NormValidationError(
                    f"{norm.source_path}: active norm requires non-active target "
                    f"{relation.target!r}"
                )

    return NormIndex(norms=norms)


def _split_frontmatter(path: Path, text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "+++":
        _raise(path, "norm must begin with +++ TOML frontmatter")
    closing = next(
        (index for index, line in enumerate(lines[1:], 1) if line.strip() == "+++"),
        None,
    )
    if closing is None:
        _raise(path, "norm frontmatter is missing its closing +++ delimiter")
    frontmatter = "".join(lines[1:closing])
    body = "".join(lines[closing + 1 :])
    if len(frontmatter) > _MAX_FRONTMATTER_CHARS:
        _raise(path, f"frontmatter exceeds {_MAX_FRONTMATTER_CHARS} characters")
    if len(body) > _MAX_BODY_CHARS:
        _raise(path, f"Markdown body exceeds {_MAX_BODY_CHARS} characters")
    return frontmatter, body


def _parse_scope(table: Mapping[str, object], path: Path) -> NormScope:
    allowed = {"areas", "languages", "paths", "tasks"}
    unknown = set(table) - allowed
    if unknown:
        _raise(path, f"unknown scope fields: {', '.join(sorted(unknown))}")
    areas = _selector_list(table, "areas", path)
    languages = _selector_list(table, "languages", path)
    paths = _string_list(table, "paths", path, 160)
    tasks = _selector_list(table, "tasks", path)
    return NormScope(areas=areas, languages=languages, paths=paths, tasks=tasks)


def _parse_relations(value: object, path: Path, norm_id: str) -> tuple[NormRelation, ...]:
    if not isinstance(value, list):
        _raise(path, "relations must be an array of tables")
    relations: list[NormRelation] = []
    allowed_types: tuple[RelationType, ...] = (
        "requires",
        "conflicts",
        "supersedes",
        "example_of",
        "related_to",
    )
    for index, item in enumerate(value):
        table = _mapping(item, path, f"relations[{index}]")
        if set(table) != {"type", "target"}:
            _raise(path, f"relations[{index}] must contain only type and target")
        relation_type: RelationType = _literal(
            table, "type", path, allowed_types, label=f"relations[{index}].type"
        )
        target = _bounded_string(table, "target", path, 120, label=f"relations[{index}].target")
        if not _ID_PATTERN.fullmatch(target):
            _raise(path, f"invalid relation target: {target!r}")
        if target == norm_id:
            _raise(path, f"norm {norm_id!r} cannot relate to itself")
        relations.append(NormRelation(type=relation_type, target=target))
    if len(set(relations)) != len(relations):
        _raise(path, "relations must be unique")
    return tuple(sorted(relations))


def _parse_provenance(table: Mapping[str, object], path: Path) -> NormProvenance:
    allowed = {"kind", "source", "owner", "reviewed_at"}
    unknown = set(table) - allowed
    missing = {"kind", "source"} - set(table)
    if unknown:
        _raise(path, f"unknown provenance fields: {', '.join(sorted(unknown))}")
    if missing:
        _raise(path, f"missing provenance fields: {', '.join(sorted(missing))}")
    kind: ProvenanceKind = _literal(
        table,
        "kind",
        path,
        ("repository", "upstream", "personal", "external"),
        label="provenance.kind",
    )
    source = _bounded_string(table, "source", path, 500, label="provenance.source")
    owner = _optional_bounded_string(table, "owner", path, 120, label="provenance.owner")
    reviewed_text = _optional_bounded_string(
        table, "reviewed_at", path, 10, label="provenance.reviewed_at"
    )
    reviewed_at: date | None = None
    if reviewed_text is not None:
        try:
            reviewed_at = date.fromisoformat(reviewed_text)
        except ValueError as error:
            raise NormValidationError(
                f"{path}: provenance.reviewed_at must be an ISO date"
            ) from error
    return NormProvenance(kind=kind, source=source, owner=owner, reviewed_at=reviewed_at)


def _parse_sections(path: Path, body: str) -> tuple[NormSection, ...]:
    sections: list[NormSection] = []
    current_name: str | None = None
    current_lines: list[str] = []

    def finish_section() -> None:
        if current_name is None:
            return
        content = "\n".join(current_lines).strip()
        if not content:
            _raise(path, f"section {current_name!r} cannot be empty")
        limit = _SECTION_LIMITS[current_name]
        if len(content) > limit:
            _raise(path, f"section {current_name!r} exceeds {limit} characters")
        sections.append(NormSection(name=current_name, content=content))

    for line in body.splitlines():
        if line.startswith("## "):
            finish_section()
            heading = line[3:].strip()
            if heading not in _SECTION_ORDER:
                _raise(path, f"unknown level-two section: {heading!r}")
            if any(section.name == heading for section in sections):
                _raise(path, f"duplicate section: {heading!r}")
            current_name = heading
            current_lines = []
        elif current_name is None:
            if line.strip():
                _raise(path, "Markdown body cannot contain text before the first section")
        else:
            current_lines.append(line)
    finish_section()

    names = tuple(section.name for section in sections)
    missing = _REQUIRED_SECTIONS - set(names)
    if missing:
        _raise(path, f"missing Markdown sections: {', '.join(sorted(missing))}")
    expected_order = tuple(name for name in _SECTION_ORDER if name in names)
    if names != expected_order:
        _raise(path, "Markdown sections are not in canonical order")
    return tuple(sections)


def _mapping(value: object, path: Path, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _raise(path, f"{label} must be a table")
    return cast("Mapping[str, object]", value)


def _integer(table: Mapping[str, object], key: str, path: Path) -> int:
    value = table.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        _raise(path, f"{key} must be an integer")
    return value


def _bounded_string(
    table: Mapping[str, object],
    key: str,
    path: Path,
    maximum: int,
    *,
    label: str | None = None,
) -> str:
    value = table.get(key)
    field = label or key
    if not isinstance(value, str) or not value.strip():
        _raise(path, f"{field} must be a non-empty string")
    if len(value) > maximum:
        _raise(path, f"{field} exceeds {maximum} characters")
    return value


def _optional_bounded_string(
    table: Mapping[str, object],
    key: str,
    path: Path,
    maximum: int,
    *,
    label: str,
) -> str | None:
    if key not in table:
        return None
    return _bounded_string(table, key, path, maximum, label=label)


def _literal(
    table: Mapping[str, object],
    key: str,
    path: Path,
    allowed: Sequence[Value],
    *,
    label: str | None = None,
) -> Value:
    value = table.get(key)
    field = label or key
    if not isinstance(value, str) or value not in allowed:
        _raise(path, f"{field} must be one of: {', '.join(allowed)}")
    return cast("Value", value)


def _string_list(
    table: Mapping[str, object], key: str, path: Path, maximum: int
) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list):
        _raise(path, f"scope.{key} must be an array")
    values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > maximum:
            _raise(path, f"scope.{key} entries must be non-empty strings up to {maximum} chars")
        values.append(item)
    if len(set(values)) != len(values):
        _raise(path, f"scope.{key} entries must be unique")
    return tuple(sorted(values))


def _selector_list(table: Mapping[str, object], key: str, path: Path) -> tuple[str, ...]:
    values = _string_list(table, key, path, 80)
    for value in values:
        if not _SELECTOR_PATTERN.fullmatch(value):
            _raise(path, f"scope.{key} contains invalid selector {value!r}")
    return values


def _matches_value(selectors: tuple[str, ...], value: str | None) -> bool:
    return not selectors or (value is not None and value in selectors)


def _matches_path(patterns: tuple[str, ...], value: str | None) -> bool:
    if not patterns:
        return True
    if value is None:
        return False
    normalized = value.replace("\\", "/").lstrip("./")
    candidate = PurePosixPath(normalized)
    for pattern in patterns:
        if candidate.match(pattern):
            return True
        reduced = pattern
        while "**/" in reduced:
            reduced = reduced.replace("**/", "", 1)
            if candidate.match(reduced):
                return True
    return False


def _status_is_enabled(norm: Norm, include_drafts: bool, include_deprecated: bool) -> bool:
    return (
        norm.status == "active"
        or (norm.status == "draft" and include_drafts)
        or (norm.status == "deprecated" and include_deprecated)
    )


def _raise(path: Path, message: str) -> NoReturn:
    raise NormValidationError(f"{path}: {message}")
