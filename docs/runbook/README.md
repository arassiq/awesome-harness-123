# Command runbook

This is the human-readable command surface. It will eventually be generated from the same canonical registry used by the CLI, MCP adapter, and machine-readable schemas.

## Development

| Command | Meaning |
| --- | --- |
| `uv sync --extra dev` | Create/update the environment and install development tools. |
| `uv run harness doctor` | Report harness and local prerequisite information. |
| `uv run harness validate` | Check the repository's required structure. |
| `uv run pytest` | Run unit tests. |
| `uv run ruff check .` | Run static lint checks. |
| `uv run mypy src` | Run strict type checks. |

## Harness CLI

| Command | Meaning | Writes? |
| --- | --- | --- |
| `harness init [PATH]` | Add minimal harness metadata without overwriting existing files. | Yes |
| `harness init [PATH] --dry-run` | Preview initialization. | No |
| `harness validate [PATH]` | Validate a repository. | No |
| `harness validate [PATH] --json` | Emit validation as structured JSON. | No |
| `harness doctor [--json]` | Inspect local prerequisites. | No |
| `harness eval` | Show the current eval scaffold. | No |

## Superset

New Superset workspaces run `uv sync --extra dev` through `.superset/config.json`.

If workspace setup fails:

1. Confirm `uv --version` works in the workspace terminal.
2. Run `uv sync --extra dev` manually and retain the complete error.
3. Run `uv run harness doctor --json`.
4. Do not add credentials to the shared Superset config.

## OpenCode

OpenCode is not installed automatically by this repository. The harness will pin and document a tested version after the baseline runtime experiment.
