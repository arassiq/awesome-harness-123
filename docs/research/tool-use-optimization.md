# Tool-use optimization in OpenCode

## Status

Stretch track. Begin after the baseline eval runner records task success, tool traces, token usage, latency, and resumption outcomes.

## Core question

Which combination of OpenCode-native tools, custom tools, plugins, fixed tool bundles, and MCP adapters yields the highest task success per unit of context and latency without damaging prompt-cache continuity?

## Hypotheses

1. A small stable base bundle will outperform exposing every available tool.
2. Fixed bundles selected by mode will preserve cache prefixes better than arbitrary per-turn schemas.
3. Native OpenCode tools will have lower operational overhead for local-only behavior.
4. MCP will be most valuable at cross-runtime and remote-service boundaries.
5. Bounded structured output plus artifact references will outperform raw tool dumps.

## Experimental matrix

Compare the same tasks under:

- built-in tools only;
- built-ins plus a small native custom-tool bundle;
- the equivalent local MCP tool bundle;
- a broad all-tools configuration;
- fixed mode bundles: implement, review, teach, and eval.

Measure:

- end-to-end task success;
- correct first tool selection;
- invalid calls and repair turns;
- tool-schema input tokens;
- tool-result tokens;
- time to first useful action and total latency;
- prompt-cache reads/writes or the closest provider-visible proxy;
- compaction frequency and post-compaction recovery quality.

## Decision rule

No tool exposure strategy becomes a default because it feels cleaner. It must improve the relevant eval score without an unacceptable cache, latency, safety, or maintenance regression.
