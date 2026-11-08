# awesome-harness-123

[![CI](https://github.com/arassiq/awesome-harness-123/actions/workflows/ci.yml/badge.svg)](https://github.com/arassiq/awesome-harness-123/actions/workflows/ci.yml)

A local-first, runtime-portable harness for making coding agents more reliable across long-running development work.

The project treats context, compaction, tool exposure, repository state, and evaluation as observable systems rather than hidden prompt details. OpenCode is the first target runtime, but the harness is designed so its policy and evidence can also be projected into other agent runtimes.

## Status

This repository is an early executable harness. It currently provides:

- a dependency-light `harness` CLI;
- a safe `init` → `plan` → `apply` lifecycle for managed runtime projections;
- a deterministic, bounded coding-norm schema and resolver;
- a generated OpenCode plugin that exposes norm resolution as a tool;
- the Cliff compaction core, portable configuration, and tests (OpenCode mutation remains
  experimental and disabled);
- a first-class location for eval cases and results;
- a canonical schema area for tool definitions;
- Superset workspace bootstrap configuration;
- durable design, research, and operator documentation.

The implementation deliberately starts small. Decisions about compaction and tool routing will be accepted only after repeatable evaluations exist.

## Quick start

Requirements: Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run harness doctor
uv run harness validate
uv run pytest
```

Install the portable baseline in another repository:

```bash
git init
harness init /path/to/repository
harness plan /path/to/repository
harness apply /path/to/repository
```

Or use the one-step form after you understand what it owns:

```bash
harness init /path/to/repository --apply
```

Local mode is the default. It installs a concise `AGENTS.md`, private indexed docs and evals beneath
`.harness/`, the complete shared norm library, and experimental Cliff settings. These control files
are added to the clone-local `.git/info/exclude`, so `git status` remains clean and nothing is
pushed. Use `harness init --tracked --apply` when the team should commit the baseline; tracked mode
places docs and evals at the repository root.

The three current Python norms are draft authoring scaffolds, not active policy. Existing project
files are never overwritten. `apply` owns only dedicated generated files beneath
`.opencode/plugins/awesome-harness/` and refuses to overwrite drifted or pre-existing files.

Cliff is configured with `enabled = false`: OpenCode's current public plugin API cannot persist a
structured replacement message window, so the harness does not claim active Cliff behavior before
that adapter boundary and its eval gates are resolved.

## Direction

The first milestones are:

1. Integrate the tested Cliff core with OpenCode in shadow mode.
2. Compare Cliff and native compaction while measuring cache discontinuity and task success.
3. Add deterministic automatic norm scoping and required-norm coverage checks.
4. Add durable task checkpoints and resumption tests.
5. Introduce fixed, mode-specific tool bundles.
6. Explore content-addressed repository indexing and invalidation.

The OpenCode tool-use study is intentionally downstream of the eval baseline. It will compare task success, tool-selection accuracy, invalid calls, repair turns, schema tokens, output tokens, latency, and prompt-cache behavior.

## Documentation

- [Documentation index](docs/INDEX.md)
- [Harness foundations](docs/design/harness-foundations.md)
- [Tool-use optimization](docs/research/tool-use-optimization.md)
- [Command runbook](docs/runbook/README.md)
- [Canonical tool registry](docs/specs/tool-registry.md)
- [Evaluation scaffold](evals/README.md)

## Repository layout

```text
src/awesome_harness/  CLI and core behavior
scaffold/             portable agent, docs, and eval baseline
norms/                canonical shared norm library vendored by init
tests/                executable unit tests
evals/                benchmark cases and result conventions
schemas/              machine-readable public contracts
docs/design/          architecture and problem framing
docs/research/        research questions and evidence
docs/runbook/         operator-facing command reference
.superset/            reproducible workspace lifecycle
```

## Contributing

Start with `docs/design/harness-foundations.md`. Keep policy runtime-neutral, put runtime-specific behavior behind adapters, and accompany behavioral changes with an eval or test.

## License

No license has been selected yet. Until one is added, all rights are reserved.
