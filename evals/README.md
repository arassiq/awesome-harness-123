# Evaluations

Evaluations are the acceptance boundary for changes to compaction, context assembly, routing, tools, and checkpoints.

## Case shape

Each versioned case identifies:

- a stable ID and task prompt;
- fixture/setup requirements;
- expected observable outcomes;
- allowed and forbidden side effects;
- metrics to capture.

`cases/smoke.json` is a schema seed, not yet an executable benchmark.

## Result shape

Generated results belong under `.harness/runs/` and are ignored by Git. A promoted summary may be committed when it records the harness version, runtime/model identity, configuration hash, task results, token metrics, latency, tool trace summary, and known limitations.
