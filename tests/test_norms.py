from pathlib import Path

import pytest

from awesome_harness.norms import (
    NormValidationError,
    ScopeContext,
    build_norm_index,
    load_norm,
    render_norm_bundle,
)


def _write_norm(
    path: Path,
    norm_id: str,
    *,
    status: str = "active",
    priority: str = "advisory",
    delivery: str = "scoped",
    scope: str = 'areas = ["backend"]\nlanguages = ["python"]\npaths = ["**/*.py"]',
    relations: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    relation_value = "" if relations else "relations = []\n"
    path.write_text(
        f'''+++
schema_version = 1
id = "{norm_id}"
version = 1
title = "Test norm"
summary = "A bounded test norm."
status = "{status}"
priority = "{priority}"
delivery = "{delivery}"
{relation_value}

[scope]
{scope}
{relations}
[provenance]
kind = "repository"
source = "test fixture"
+++

## Rule

Apply the fixture rule.

## Rationale

This text exercises deterministic loading.
''',
        encoding="utf-8",
    )


def test_load_valid_norm(tmp_path: Path) -> None:
    path = tmp_path / "backend" / "python" / "api.md"
    _write_norm(path, "backend.python.api")

    norm = load_norm(path)

    assert norm.id == "backend.python.api"
    assert norm.scope.languages == ("python",)
    assert tuple(section.name for section in norm.sections) == ("Rule", "Rationale")
    assert norm.provenance.source == "test fixture"


def test_index_rejects_duplicate_ids(tmp_path: Path) -> None:
    _write_norm(tmp_path / "first.md", "backend.python.api")
    _write_norm(tmp_path / "second.md", "backend.python.api")

    with pytest.raises(NormValidationError, match="duplicate norm id"):
        build_norm_index(tmp_path)


def test_index_rejects_missing_relation_target(tmp_path: Path) -> None:
    relations = '''
[[relations]]
type = "requires"
target = "backend.python.missing"

'''
    _write_norm(tmp_path / "api.md", "backend.python.api", relations=relations)

    with pytest.raises(NormValidationError, match="does not exist"):
        build_norm_index(tmp_path)


def test_index_rejects_unnamed_navigation_markdown(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("# Not a norm\n", encoding="utf-8")

    with pytest.raises(NormValidationError, match="must begin with"):
        build_norm_index(tmp_path)


def test_index_has_stable_id_order(tmp_path: Path) -> None:
    _write_norm(tmp_path / "z-file.md", "backend.python.testing")
    _write_norm(tmp_path / "a-file.md", "backend.python.api")

    index = build_norm_index(tmp_path)

    assert tuple(norm.id for norm in index.norms) == (
        "backend.python.api",
        "backend.python.testing",
    )


def test_scope_resolution_includes_always_scoped_and_required_norms(tmp_path: Path) -> None:
    _write_norm(
        tmp_path / "security.md",
        "core.security.credentials",
        priority="required",
        delivery="always",
        scope="",
    )
    requires = '''
[[relations]]
type = "requires"
target = "backend.python.testing"

'''
    _write_norm(
        tmp_path / "api.md",
        "backend.python.api",
        scope=(
            'areas = ["backend"]\n'
            'languages = ["python"]\n'
            'paths = ["src/**/*.py"]\n'
            'tasks = ["implementation"]'
        ),
        relations=requires,
    )
    _write_norm(
        tmp_path / "testing.md",
        "backend.python.testing",
        scope='areas = ["backend"]\nlanguages = ["python"]\ntasks = ["testing"]',
    )
    _write_norm(
        tmp_path / "frontend.md",
        "frontend.typescript.components",
        scope='areas = ["frontend"]\nlanguages = ["typescript"]',
    )
    _write_norm(
        tmp_path / "example.md",
        "backend.python.timeout_example",
        delivery="on_demand",
        scope='areas = ["backend"]\nlanguages = ["python"]',
    )
    index = build_norm_index(tmp_path)

    resolved = index.resolve(
        ScopeContext(
            area="backend",
            language="python",
            path="src/api.py",
            task="implementation",
        )
    )

    assert tuple(norm.id for norm in resolved) == (
        "backend.python.api",
        "backend.python.testing",
        "core.security.credentials",
    )


def test_scope_resolution_excludes_drafts_by_default(tmp_path: Path) -> None:
    _write_norm(tmp_path / "draft.md", "backend.python.draft", status="draft")
    index = build_norm_index(tmp_path)
    context = ScopeContext(area="backend", language="python", path="service.py")

    assert index.resolve(context) == ()
    assert tuple(norm.id for norm in index.resolve(context, include_drafts=True)) == (
        "backend.python.draft",
    )


def test_render_bundle_is_stable_and_omits_frontmatter(tmp_path: Path) -> None:
    _write_norm(tmp_path / "z.md", "backend.python.testing")
    _write_norm(tmp_path / "a.md", "backend.python.api")
    index = build_norm_index(tmp_path)

    rendered = render_norm_bundle(tuple(reversed(index.norms)))

    assert rendered.index("backend.python.api") < rendered.index("backend.python.testing")
    assert "schema_version" not in rendered
    assert "### Rule" in rendered
