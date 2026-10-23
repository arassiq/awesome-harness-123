# Agent instructions

## Purpose

This repository builds and evaluates a portable development-agent harness. Preserve the separation between canonical policy and runtime-specific adapters.

## Working rules

- Read `docs/design/harness-foundations.md` before changing architecture.
- Treat evals as product behavior: changes to routing, context, tools, or compaction require evidence.
- Keep generated interfaces derived from one canonical definition when practical.
- Prefer bounded structured outputs over long prose or raw tool dumps.
- Preserve stable schema names and ordering when cache continuity matters.
- Never commit credentials, model-provider keys, local traces containing secrets, or private source material.
- Do not autonomously modify canonical harness policy. Propose policy changes for review.

## Verification

Run before committing:

```bash
uv run ruff check .
uv run mypy src
uv run pytest
uv run harness validate
```
