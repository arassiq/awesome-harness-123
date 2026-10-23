# awesome-harness-123

[![CI](https://github.com/arassiq/awesome-harness-123/actions/workflows/ci.yml/badge.svg)](https://github.com/arassiq/awesome-harness-123/actions/workflows/ci.yml)

A local-first, runtime-portable harness for making coding agents more reliable across long-running development work.

The project treats context, compaction, tool exposure, repository state, and evaluation as observable systems rather than hidden prompt details. OpenCode is the first target runtime, but the harness is designed so its policy and evidence can also be projected into other agent runtimes.

## Status

This repository is an early executable scaffold. It currently provides:

- a dependency-light `harness` CLI;
- repository initialization and validation commands;
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

Initialize harness metadata in another repository:

```bash
uv run harness init /path/to/repository
```

Preview without writing:

```bash
uv run harness init /path/to/repository --dry-run
```

## Direction

The first milestones are:

1. Establish baseline evals and trace capture.
2. Add durable task checkpoints and resumption tests.
3. Compare compaction strategies while measuring cache discontinuity.
4. Introduce fixed, mode-specific tool bundles.
5. Compare OpenCode-native custom tools with an MCP adapter.
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
