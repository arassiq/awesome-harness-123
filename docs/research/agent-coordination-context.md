# Efficient agent coordination, verification, and repository context

Status: Research synthesis and design input; no protocol or runtime behavior is approved by this
document.
Last reviewed: 2026-11-16

## Core problem

Small worker models can perform implementation cheaply, but the cost advantage disappears if their
transcripts, source reads, diffs, and raw tool output are forwarded to a frontier orchestrator. An
overly compressed summary creates the opposite failure: the orchestrator cannot tell whether the
work is correct, stale, blocked, or safe to accept.

The target is therefore **decision-relevant information density**. The orchestrator should receive
enough grounded state to choose the next correct action while recoverable bulk remains outside its
context.

This work spans three related but distinct mechanisms:

1. a bounded manager-to-worker work order;
2. a bounded worker-to-manager report with selectively retrievable evidence;
3. deterministic verification and repository indexes that make those reports checkable without
   replaying agent history.

Cliff compaction remains responsible for one agent's long conversation. This proposal addresses
information crossing between agents. Coding norms remain independently selected project policy.

## Responsibility model

The frontier agent remains the manager and final decision owner. Workers are bounded implementation
capabilities, not peers that silently inherit product or policy authority.

### Downward work order

The manager should send a medium-level contract containing:

- objective and expected deliverable;
- allowed scope;
- non-negotiable constraints;
- acceptance criteria and verification profile;
- authority boundaries;
- legitimate escalation conditions;
- a bounded reporting budget.

The worker owns local investigation, implementation planning, editing, debugging, and verification.
It should not return ordinary implementation thinking to the manager. It may escalate only when the
remaining issue requires missing authority, missing external information, resolution of conflicting
requirements, an irreversible architectural choice, or another condition named in the work order.

An escalation should still contain attempted actions, observed evidence, the worker's recommendation,
and the smallest decision required. “The manager should figure this out” is not an acceptable worker
result.

### Upward action-state-result report

The leading communication abstraction is:

```text
Action
    What the worker actually did.

Grounded state
    What is observably true after the action, with evidence attached to factual claims.

Result
    The artifact or behavior produced for downstream use and its acceptance status.
```

`Action` is an intervention, not private reasoning. `Grounded state` must distinguish observations
from interpretation. `Result` is the externally useful consequence, not a declaration that editing
stopped.

Example:

```text
Action
    Changed the order worker to bound retries at three attempts.

Grounded state
    The diff affects src/workers/orders.py. The LocalStack E2E profile collected three tests,
    returned exit code 0, and recorded three passes. Each claim points to a diff or run artifact.

Result
    Exhausted orders enter the dead-letter queue and the assigned acceptance profile passed.
```

The worker may request a manager action only for a legitimate escalation. The request is a claim,
not an authoritative priority classification.

## Worker claims versus harness observations

A small model may fail to notice that it is looping, misclassify risk, or confidently report
completion. The protocol must not rely on a worker-authored `attention required` or confidence field
as truth.

The orchestrator should receive two distinguishable channels:

```text
Worker report
    Semantic action, result, recommendation, and unresolved issue.

Harness observation
    Git state, exact verification result, repeated command fingerprints, repeated failures,
    lack of repository progress, resource budgets, stale sequence, and artifact identity.
```

Priority can then be derived by orchestration policy from observable conditions and the dependency
graph. Examples include failed required verification, an unresolved external dependency, a stale
report, repeated identical failures, or exhaustion of a configured step budget. Thresholds still
require evaluation; their values should not be presented as universal.

## Progressive disclosure

The current hypothesis uses three tiers.

### Tier 0: routing signal

A very small status record identifies task, sequence, state transition, and the location of the
latest report. It exists so the manager can sort many workers without loading every report.

### Tier 1: bounded current-state report

The report contains the latest action-state-result record, unresolved items, acceptance outcomes,
and evidence identifiers. A newer report supersedes the older report for the same task; the manager
does not ingest a growing handoff history.

A 4,096-byte ceiling was discussed as an initial maximum, not an evidence-backed target. Ordinary
checkpoints should be substantially smaller, and some progress events may need no Tier 1 report.
Budget variants must be evaluated rather than promoted by intuition.

### Tier 2: evidence artifacts

Source, diffs, logs, test reports, commits, and other recoverable artifacts stay outside the report.
The manager retrieves an artifact only to verify a material claim, inspect a failure, resolve a
conflict, or review a risky change.

Every factual claim should identify its supporting evidence. A generic list of references detached
from claims is insufficient. Evidence references do not imply that all evidence should be loaded;
they make selective verification possible.

Routine heartbeats should remain in a coordinator store and outside frontier-model context. Reports
should occur at material checkpoints, decision boundaries, blockers, review-ready states,
completion, failure, or explicit requests.

## Deterministic and model-authored information

The harness should produce observable verification fields without asking a model to summarize them:

- exact command and repository-relative working directory;
- repository revision and dirty-tree content identity;
- verification-profile and environment fingerprints;
- exit code and process status;
- collected, passed, failed, skipped, and errored counts;
- exact failing test identifiers;
- artifact locations, byte counts, and content digests;
- timeout, truncation, infrastructure-failure, and cleanup status;
- report sequence validity and stale-report detection.

Timestamps and duration are recorded observations but are not repeatable values. Stable schema names,
ordering, and serialization should make the projection of one recorded run byte-stable.

Model-authored information includes the conceptual action, semantic effect, diagnosis,
recommendation, and unresolved architectural question. These statements must remain visibly
distinct from harness observations and link to evidence when they make factual claims.

## End-to-end verification without context growth

End-to-end testing is not limited to browser applications. A public workflow may begin at an API,
CLI, queue event, scheduled job, data pipeline, or harness command.

A LocalStack-backed workflow can exercise the application, workers, database, and AWS-facing code
locally. Its result must be described as a local system or E2E test with emulated AWS dependencies,
not proof of compatibility with the real service. A smaller provider contract suite may be needed
for behaviors LocalStack cannot establish.

Test data belongs with the target repository as fixtures, factories, seed scripts, or sanitized
representative payloads. The harness should run and report them, not invent domain data.

Tests do not teach the agent how to behave. The layers are:

```text
Norm
    Project-approved verification principles.

Verification profile
    Exact setup, command, timeout, teardown, environment, and artifact contract.

Application tests
    Observable correctness of the target system.

Harness verifier
    Deterministic execution record and bounded model-facing projection.

Harness E2E test
    Proof that the public verification path performs and reports the workflow correctly.
```

Full stdout, stderr, Docker logs, JUnit XML, traces, and fixture diagnostics should be written under a
run-artifact directory. The initial model-facing result should contain only outcome, counts, failing
test IDs, a bounded error excerpt, limitations, and artifact references. Failure investigation
should retrieve one relevant slice at a time.

A proposed verification cadence is:

1. run the smallest affected unit or integration test during iteration;
2. run affected local E2E scenarios at coherent checkpoints;
3. run the complete relevant E2E profile before review or completion;
4. run broader provider contract or release suites at their explicit boundary.

Verification reuse may be keyed by repository tree identity, dirty-file identities, test command,
fixture version, environment configuration, and container-image digests. Reuse is valid only while
all relevant inputs remain unchanged. Incorrect dependency tracking could reuse a stale pass, so the
first implementation should prefer conservative invalidation.

Important costs and failure modes include runtime, container resource use, flakiness, eventual
consistency, test-data maintenance, LocalStack/provider divergence, poor E2E failure localization,
and agent overfitting to visible tests. E2E coverage should complement focused unit and integration
tests rather than replace them.

## Content-addressed repository navigation

Each harnessed repository may benefit from an incrementally maintained index, but the index must be
a navigation cache rather than repository truth.

The first useful layer can be deterministic:

- repository-relative path and content identity;
- language and file role;
- symbols and signatures;
- imports and dependencies;
- implementation-to-test relationships;
- configuration references;
- generated, vendored, binary, or excluded classification;
- analyzer version.

Derived records should be keyed by `(content hash, analyzer version)`. A query must validate current
content identity before exposing a cached record. On mismatch, the record is stale and the harness
must reanalyze or fall back to the current file. A model-generated summary must never survive a
content mismatch.

Committed files can reuse Git blob identities across branches and worktrees. Uncommitted files need
a working-tree overlay keyed by their current bytes. Paths alone are not valid cache keys because
the same path may contain different content in different worktrees.

The intended retrieval path is:

```text
Task question
    -> deterministic search or index
    -> bounded candidate list with reasons and content identities
    -> exact read of current relevant sections
    -> implementation
```

The agent should still read current source before editing. The index locates truth; it does not
replace truth. File watchers may improve freshness, but retrieval-time hash validation is the
correctness boundary.

Symbols, imports, configuration, and test relations already form a lightweight graph. Semantic or
graph retrieval may later help ambiguous conceptual searches, but it is not required for the first
content-addressed baseline. The index should be evaluated against `rg`, file discovery, and direct
reads before adding embeddings or model-generated summaries.

Evidence in agent reports can use the same identities. If another worker changes a referenced file,
the orchestrator can detect that the report's evidence no longer describes the current content.

## Research findings

### Protocolized Action-state Communication and Transmission

[What Should Agents Say? Action-state Communication for Efficient Multi-Agent Systems](https://arxiv.org/abs/2606.05304)
studies full content, concise generation, conclusion-only, brief summaries, and artifact-only
communication. It reports that no fixed strategy is universally best, but useful messages preserve
action-centered information and enough state to ground the result.

PACT projects private agent output into public `Action`, `State`, and `Result` records. Its ablation
reports worse F1 and higher token use when only the result is retained, supporting grounded action
state rather than unsupported conclusions. In its Qwen3-14B SWE-bench Verified coding-harness
experiments, the OpenHands port increased resolved instances from 97/500 to 115/500 and reduced
tokens per resolved task by 10.3%. The SWE-agent port reduced input tokens by 50.4% and tokens per
resolved task by about 47%, while resolved instances decreased from 128/500 to 121/500.

These results support a compact public-message boundary and also show why cost must not be optimized
without task success. The paper is a recent preprint, evaluates limited harnesses and models, and
does not establish our report schema or byte budget.

### Persistent artifacts instead of conversational copying

Anthropic's
[multi-agent research system write-up](https://www.anthropic.com/research/multi-agent-research-system)
describes subagents writing outputs to persistent artifacts and returning lightweight references to
reduce information loss and token overhead. Its
[context-engineering guidance](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)
likewise separates detailed subagent context from lead-agent synthesis and recommends external
structured state for long-horizon work.

This supports lazy evidence artifacts, but research workflows are not identical to coding agents.
The harness must still test whether selective evidence causes missed implementation defects.

### Controlled communication and calibrated trust

[DarkForest](https://arxiv.org/abs/2605.25188) keeps agent generations independent, parses them into
structured observations, and treats self-reported confidence as a weak input combined with calibrated
agent reliability and support patterns. Raw traces are not exposed by default. Its evaluated tasks
are primarily answer-selection problems rather than long-running repository edits, so it does not
directly validate our coding architecture. It does support the inference that worker confidence or
attention labels should not control orchestration without external observations.

[Cost-Effective Communication](https://arxiv.org/abs/2511.13193) treats communication bandwidth as
scarce and reports that learned communication can develop strategic silence.
[ACTS](https://arxiv.org/abs/2610.25851) dynamically selects who communicates based on roles and
execution state and reports lower token use across its benchmarks. These are evidence against
free-for-all communication, not adopted dependencies or proof that a learned router is necessary.

### Manager ownership and bounded workers

OpenAI's
[orchestration guidance](https://developers.openai.com/api/docs/guides/agents/orchestration)
distinguishes transferring conversation ownership through a handoff from retaining a manager that
calls specialists as bounded tools. The latter more closely matches the desired frontier-manager
architecture: workers execute bounded tasks while the manager remains responsible for integration
and the final user-facing decision.

## Evaluation hypotheses

### Handoff communication

Compare at least:

1. full worker transcript;
2. unstructured prose summary;
3. action-state-result report with all evidence injected;
4. action-state-result report with evidence retrieved on demand.

Measure task acceptance accuracy, incorrect acceptance, unnecessary rejection, critical omission,
claim-to-evidence faithfulness, frontier input and output tokens, evidence retrieval tokens,
repeated file reads, latency, cost, stale-report handling, and final task success.

Seed verified success, unsupported success claims, failed checks, unresolved blockers, contradictory
worker and harness state, stale evidence, and workers stuck in repeated loops. Smaller messages are a
failure if they cause incorrect acceptance, redundant work, or broad evidence retrieval.

### Verification pathway

Exercise the user-facing path from verification-profile selection through environment setup, test
execution, artifact capture, bounded projection, failure drill-down, and teardown. Include pass,
assertion failure, infrastructure failure, timeout, excessive logs, secret redaction, missing machine
output, interruption, and cache invalidation.

### Repository index

Compare direct deterministic discovery with indexed retrieval on repeated tasks. Measure candidate
recall, bytes exposed to the model, unnecessary reads, stale-record rejection, index update cost,
task success, and whether the agent reads exact current code before editing. Include multiple
worktrees with the same path and different content.

## Open questions before implementation design

1. What is the smallest report that preserves correct orchestration decisions for coding tasks?
2. Should communication budgets vary by checkpoint, blocker, review, and completion state?
3. Which observable signals are reliable enough for deterministic loop escalation?
4. How are acceptance criteria represented so the worker cannot redefine completion?
5. Which claims require evidence, and which fields are requests or recommendations rather than
   factual claims?
6. What artifact locator works across OpenCode, Codex, Superset, local worktrees, and future remote
   workers?
7. Where should transient coordination live across worktrees while durable decisions remain in Git?
8. Which verification-run inputs are sufficient for safe cache reuse?
9. How should real-provider contract tests complement LocalStack without exposing credentials or
   imposing excessive cost?
10. Which languages and parsers belong in the first deterministic repository index?
11. How should the skill be discovered without adding the full protocol to always-loaded
    `AGENTS.md` context?

## Explicit non-decisions

- No handoff schema, byte budget, storage engine, transport, or runtime adapter is approved yet.
- No worker-authored attention or confidence score is trusted as orchestration truth.
- LocalStack is not required for every project and does not prove real AWS compatibility.
- E2E tests do not replace focused unit and integration tests.
- The repository index is not an authority and must not permit editing from stale summaries.
- Embeddings, Graph RAG, learned communication routing, and model-generated file summaries are not
  required for the first deterministic baseline.
