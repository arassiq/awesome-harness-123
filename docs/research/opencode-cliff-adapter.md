# OpenCode Cliff adapter: verified surface and unresolved risks

Status: implementation research, not promoted policy
Last checked: 2026-11-04 against OpenCode 2.2.1

## Question

Can the runtime-neutral Cliff core replace only the model-facing OpenCode history while preserving
the complete canonical transcript, keeping a compacted prefix byte-stable between cliffs, and
avoiding a second native compaction system?

## Verified OpenCode surface

OpenCode V2 discovers local plugins beneath `.opencode/plugins/`. A plugin default-exports a stable
ID and `setup(ctx)`. The documented `session.hook("context", ...)` event exposes assembled system
parts, messages, tools, and request options immediately before an agent model request. The official
documentation says hook changes affect the outgoing request rather than persisted history.

Sources:

- [OpenCode V2 plugin overview](https://dev.opencode.ai/v2/docs/build/plugins/)
- [OpenCode V2 server plugin API](https://dev.opencode.ai/v2/docs/build/plugins/server/)
- [OpenCode V2 compaction](https://dev.opencode.ai/v2/docs/compaction/)

The local smoke test generated `.opencode/plugins/awesome-harness/index.ts`; OpenCode 2.2.1
discovered the entrypoint and emitted no plugin-load error. The current projection registers only
the norm resolver. It does not mutate session context.

As of 2026-11-07, the public V2 `session.hook("compaction")` result can supply a summary string but
not a structured replacement message list. OpenCode core has an internal replacement mechanism,
but it is not available to ordinary plugins. Rendering a Cliff window into a prose summary would
discard its message structure; pruning only the outgoing context would race OpenCode's durable
native compaction lifecycle. Active Cliff mode therefore remains disabled rather than presenting
either workaround as equivalent.

Source: [OpenCode issue #50862](https://github.com/anomalyco/opencode/issues/50862)

## Canonical-history risk

An upstream report observed that an earlier OpenCode V2 beta persisted in-place edits of existing
message parts even though newly appended messages were transient. The report was automatically
closed as stale rather than resolved by a documented fix. Its tested version predates 2.2.1, so it
does not prove the current release is affected, but it is enough to require a canary test before the
harness rewrites real session messages.

Source: [OpenCode issue #43731](https://github.com/anomalyco/opencode/issues/43731)

The safe adapter must build fresh, ID-free outgoing message objects rather than editing persisted
parts in place, then prove through storage inspection that the canonical transcript remains
byte-identical. Documentation alone is not sufficient evidence for promotion.

## Native-compaction collision

OpenCode native automatic compaction is enabled by default. It summarizes older context, retains a
recent window, and leaves earlier messages stored. A Cliff context hook can shorten the provider
request, but OpenCode may still decide to run its own compaction from its canonical-session token
accounting. Two independent cliff thresholds would make results difficult to interpret and could
destroy the intended stable-prefix lifecycle.

Before active Cliff mode, the adapter must either:

1. own and restore the exact project-local native-compaction setting safely; or
2. integrate through OpenCode's compaction lifecycle while demonstrating that the resulting shape
   still implements the paper's non-recursive `C_n + live tail` behavior.

The harness must not overwrite an existing OpenCode config file to solve this. Any merge requires a
recorded prior value, a plan diff, drift detection, and exact restoration.

## Tool-call sequence integrity

OpenCode messages can represent an assistant tool call followed by one or more tool-result
messages. A raw last-`2K` cutoff can split that group and produce an orphan tool result rejected by
strict providers. The runtime-neutral core intentionally follows the paper's message cutoff; the
OpenCode adapter must extend a boundary to preserve complete tool-call groups and record the
deviation in evaluation metadata.

Relevant field report: [OpenCode issue #53109](https://github.com/anomalyco/opencode/issues/53109)

## Required state between cliffs

Recomputing a compacted block from the complete raw transcript on every turn is incorrect for this
project. It would move the cutoff and rewrite `C_n`, forfeiting the stable cached prefix. Per
session, the adapter needs bounded durable state containing:

- generation number;
- exact Cliff configuration and adapter version;
- compacted-block content and hash;
- canonical message ID at the compacted boundary;
- projection hash and bounded evidence counters;
- no raw source transcript or secret-bearing tool output.

Between cliffs, the outgoing projection is the original task, the unchanged `C_n`, and every
canonical message after the recorded boundary. On the next cliff, the old `C_n` is discarded and
only that live segment is compacted.

## Promotion gates

Active mutation remains blocked until these evals pass on OpenCode 2.2.1:

1. Canonical-store canary: existing message bytes are identical before and after a transformed
   request.
2. Provider-shape canary: projected tool calls and results are accepted by at least one strict
   provider path.
3. Restart test: the same `C_n` and boundary are recovered after OpenCode restarts.
4. Native-collision test: only one compaction lifecycle runs.
5. Cache test: projection prefix hashes remain unchanged between cliffs and provider cache metrics
   behave as predicted.
6. Quality comparison: Cliff, OpenCode native compaction, and unmodified context are compared on
   task success, total input/output tokens, cached tokens, latency, and recovery failures.

Until those gates pass, the shipped OpenCode projection may expose deterministic norm retrieval but
must not claim that active Cliff compaction is installed.
