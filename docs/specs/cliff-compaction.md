# CliffCompaction core specification

Status: **Experimental**
Scope: deterministic, runtime-neutral projection only

## Purpose

This module supplies the first canonical CliffCompaction transformation for the harness. It does
not install an OpenCode plugin, count provider tokens, trigger automatically, proxy requests, or
persist raw session content. A later runtime adapter will translate OpenCode messages into this
schema and send the returned projection only after its own threshold check.

Primary source: [CliffCompaction: Cost-Efficient Compaction for Long-Horizon Coding
Agents](https://arxiv.org/html/2609.26779v1), especially Algorithm 1 and Appendix B. This
implementation was written from the paper rather than copied from its open-source proxy.

## Canonical input and output

`awesome_harness.compaction` defines immutable message parts for visible text, reasoning, tool
calls, tool results, and harness-created compaction blocks. A valid input begins with:

1. one system message;
2. the original user task;
3. the active conversation segment.

`compact(messages, config)` returns a new tuple and never modifies the canonical transcript. The
projection has this stable shape:

```text
system + original task + C_n + recent 2K messages
```

The runtime adapter must retain the full original transcript separately. It must also keep the
returned prefix byte-stable between cliffs if provider prompt-cache continuity is desired.

## Deterministic rules

For the live segment, the last `2K` messages are retained unchanged, following the paper's
`turns[-2K:]` definition of `K` turn pairs. Older messages are processed as follows:

- assistant reasoning or visible narrative is retained from the beginning, up to 300 characters
  per message across all narrative parts;
- each tool call becomes a stable signature no longer than 150 characters;
- tool results of at most 500 characters are retained verbatim;
- longer tool results and other old message content are dropped;
- the system message and original task are retained unchanged.

All limits are configurable. The 300-, 150-, and 500-character defaults come directly from
Algorithm 1. `recent_turn_pairs` is intentionally required: the paper leaves `K` symbolic and does
not establish a universal default. The paper evaluates token budgets of 45K, 32K, 16K, and 8K,
but triggering remains an adapter concern because tokenization is model/provider-specific.

## Successive cliffs

The generated block is explicitly typed as `CompactionPart`. On a later call, the core locates the
latest such marker, discards every prior compacted block, and treats only messages following that
marker as the live source:

```text
S_t     = C_(t-1) + L_t
C_t     = CliffCompaction(L_t)
S_(t+1) = C_t + L_(t+1)
```

Recent original messages retained after `C_(t-1)` remain part of `L_t`; the old synthetic block
does not. This prevents recursive compaction while preserving the paper's deliberate
precision-over-recall trade-off.

## Stable evidence

Every result includes:

- the exact immutable configuration used for the transformation;
- SHA-256 hashes of the complete input, the live source segment, and the projection;
- generation number and experimental status;
- source, old, and recent message counts;
- retained and dropped source-part counts;
- retained/dropped tool-result counts;
- reduced tool-call and truncated-reasoning counts;
- number of prior compaction messages discarded.

Stable JSON serialization sorts object keys while preserving message, part, and tool-argument
order. Hashes identify exact content; they are not backups and cannot restore a transcript.

## Explicit deviations and adapter obligations

The paper operates on scaffold-specific action strings and keeps their first 150 characters. The
runtime-neutral core instead receives a tool name plus adapter-selected ordered string arguments,
renders a compact JSON signature, then applies the same 150-character cap. An adapter must put
essential recovery arguments such as path, command, or range first and render nested values
deterministically. This is the main intentional deviation and must be evaluated against real
OpenCode traces.

The paper's pseudocode models one thought field per assistant message. Runtime messages can contain
multiple text/reasoning parts, so this implementation shares one 300-character budget across those
parts in their original order. It does not summarize or paraphrase them.

The core always performs a transformation when called. It does not estimate tokens or decide when
the configured model budget has been crossed. Provider-reported usage should remain authoritative;
any local tokenizer is only an adapter-level estimate.

## Acceptance evidence

`tests/test_compaction.py` covers every transformation rule, configurable boundaries, stable
serialization and hashes, deterministic repetition, second-cliff behavior, canonical-prefix
validation, and original-input immutability. Runtime integration still requires trace evaluations
for context reduction, task quality, recovery behavior, cache resets, latency, and total cost
before this strategy can be promoted from experimental policy.
