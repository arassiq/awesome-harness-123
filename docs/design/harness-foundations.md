# Agent Harness: Problem, Foundations, and Research Direction

Status: Working design foundation  
Last updated: 2026-10-23

## Purpose of this document

This document defines the problem the agent harness is intended to solve, the observations that motivate it, the current design direction, and the research supporting that direction.

It is written for two audiences:

- Humans deciding what the harness should become and why.
- Agents that need a compact, durable account of the project without replaying the original conversations.

This is not yet an implementation specification. Statements are labeled as decisions, hypotheses, or open questions where that distinction matters. Detailed feature specifications should eventually reference this document rather than duplicating it.

## Core problem statement

Current coding-agent workflows are individually capable but operationally fragmented. Models can inspect repositories, edit files, run tools, and solve bounded tasks, yet long-running development still places a large coordination and memory burden on the human developer.

The central problem is not simply that models need more context. It is that development context is expensive, lossy, duplicated, poorly partitioned, and often stored in the wrong place.

In the current workflow:

- Multiple agent sessions run across repositories and worktrees without a shared operational picture.
- The human repeatedly explains relationships, constraints, prior research, and task status.
- Long sessions accumulate large tool outputs and repeated file reads.
- Compaction can discard important details or recursively distort earlier summaries.
- A model may finish code quickly while leaving the human unable to follow the design and implementation process.
- Existing handoffs are not deliberately optimized for either task completion or context cost.
- Repository state, conversation state, durable decisions, and transient coordination are easily conflated.
- Harness changes are often made by intuition without a reproducible way to measure whether they improved quality, cost, or usability.

The project therefore aims to build a reusable harness layer that can be installed into different repositories and workloads. It should coordinate existing tools and models rather than replace them.

## Desired outcome

Given a new or existing repository, a developer should be able to initialize the harness and receive a consistent development environment containing:

- Repository and agent operating rules.
- Model roles and routing policies.
- Configurable interaction modes.
- Context checkpointing and compaction strategies.
- Worktree-aware Git and task state.
- Compact, structured handoffs.
- Reproducible harness evaluations.
- Workload-specific profiles for software, research, RAG, and ML experimentation.

The intended relationship is:

```text
Harness                  Rules, context policy, routing, evaluation, coordination
Superset                 Workspaces, worktrees, terminals, and orchestration
OpenCode / Codex         Agent runtimes and tool loops
GLM / Qwen / Codex       Model workers
Target repository        Durable project truth and implementation state
```

## Observed user problems

### 1. Cross-session and cross-agent coordination

Many sessions may be active in different repositories or worktrees. The human currently acts as the communication bus, pointing agents toward one another and restating task relationships.

A shared Markdown file in the normal worktree is not sufficient for live coordination because separate Git worktrees do not immediately share ordinary working-tree files. Live coordination will eventually require a shared store outside an individual worktree, while accepted decisions and stable state remain version-controlled in the repository.

Priority: Deferred until the single-agent context lifecycle is reliable.

### 2. Understanding while building

The goal of using an agent is not only to maximize implementation speed. The developer also wants to understand the architecture, code, and reasoning behind what is built.

One-shot implementation conflicts with this goal. A harness must support workflows in which the agent edits real files incrementally, explains consequential choices, points to the relevant lines, and pauses at useful learning boundaries.

Priority: High.

### 3. File changes should remain visible in the editor

When a file exists in the workspace, agents should edit that file directly. They should avoid pasting large replacement code blocks into chat when the developer could instead inspect the live file or diff in Superset.

The conversational interface should emphasize decisions, questions, paths, and line references. The editor and Git diff should remain the primary presentation surfaces for code.

Priority: High.

### 4. Handoffs contain either too little signal or too much bulk

Handoffs need to support accurate resumption without copying source files, raw logs, full transcripts, or abandoned reasoning.

A handoff should contain pointers to canonical sources plus only the state that cannot be recovered cheaply:

- Task and objective.
- Current status.
- Accepted decisions and their reasons.
- Files changed.
- Verification performed and exact outcomes.
- Known failures and blockers.
- Exact next action.

Priority: High, especially as part of compaction and resumption evaluation.

### 5. Repeated repository discovery and file reads

Agents repeatedly rediscover repository structure and reread unchanged code. Operating-system file caching can make the byte reads cheap, but the contents still consume model context and may be repeatedly analyzed.

A future repository index should use Git blob hashes as content identities. Derived information remains valid while the blob hash and analyzer version remain unchanged.

Potential derived information includes:

- Language and file role.
- Symbols and signatures.
- Imports and dependencies.
- Tests and implementation relationships.
- Concise summaries.
- Last verification state.

Priority: Medium. This is promising but large enough to become a significant subsystem.

### 6. Compaction cost and context drift

Long sessions spend increasing amounts of input context on old conversation and tool output. Naive summaries may omit critical constraints, and recursively summarizing earlier summaries can compound information loss.

Compaction also interacts with provider prompt caching. Changing the prompt invalidates cache after the common prefix and requires the new context to be prefetched. Compacting too frequently may therefore reduce context size while increasing cache misses, auxiliary calls, and total cost.

Priority: Highest research and evaluation priority.

### 7. Commands and operating procedures are difficult to discover

A reusable harness will accumulate commands for initialization, validation, evaluation, checkpoints, Git state, compaction experiments, indexing, and eventually coordination. Ordinary `--help` output is insufficient for understanding when a command should be used, what it changes, what permissions it requires, and how it relates to the broader workflow.

The project should produce an interactive runbook comparable in spirit to Swagger UI: a browsable command and workflow reference generated from the same definitions used by the CLI.

Priority: High, developed alongside the CLI rather than added after it.

## Design principles

### Repository truth over conversational memory

Accepted specifications, architecture decisions, verified commands, interfaces, and current implementation state should live in version-controlled files. Conversation summaries may point to those files but should not replace them.

### Recoverable information should be referenced, not copied

Source files, diffs, test logs, and documentation can usually be reread. Context should retain the location, identity, result, or reason needed to recover them rather than carrying their entire contents indefinitely.

### Deterministic tools before model delegation

Search, file discovery, symbol lookup, Git inspection, and cache lookup should normally use deterministic tools. Delegating a read to another model may reduce parent-session context or latency, but it often increases total tokens through task description, worker reading, summarization, and parent ingestion.

### Role names over model names

Repository policies should refer to roles such as `implementation-worker` or `reviewer`. Provider and model mappings belong in configuration so a model can be replaced without rewriting the operating contract.

### Evaluation before policy promotion

Every material harness change should state:

1. The observed failure.
2. The proposed mechanism.
3. The predicted improvement.
4. The evaluation that could falsify the prediction.
5. The measured result.
6. The human decision to promote or reject it.

### Cache continuity is a first-class constraint

Context reduction and cost reduction are not equivalent. A strategy may send fewer tokens in the next request while costing more overall if it frequently rewrites the prompt prefix and forces uncached re-prefills.

Every mechanism that mutates model-facing context must therefore account for:

- How often it changes the stable prompt prefix.
- Which portion of the prior prefix remains reusable.
- How many cached tokens become uncached after the change.
- The cost and latency of prefilling the replacement context.
- How many subsequent turns amortize that reset.
- Whether a provider exposes cache usage accurately enough to verify the prediction.

The relevant optimization target is total task cost and successful task completion, not the smallest context immediately after compaction.

### Canonical policy is not autonomously mutable

Agents may propose harness-policy changes in an isolated experiment or branch. They may not silently modify or approve canonical policy.

### Executable definitions over duplicated documentation

Command metadata, configuration schemas, and examples should have one canonical machine-readable source. CLI help, Markdown runbooks, agent tool descriptions, shell completion, validation, and any interactive reference should be generated from or checked against that source.

## Interaction modes

Interaction modes should be implemented as persistent agent configurations when they require different permissions, models, or session behavior. Reusable procedures should be implemented as portable skills.

### Teaching mode

Teaching mode may edit files. Its objective includes human understanding.

Expected behavior:

1. Explain the next meaningful decision.
2. Make a small, coherent edit directly in the workspace.
3. Reference the changed file and lines.
4. Explain the relevant mechanism.
5. Pause when the next step introduces a consequential decision or new concept.
6. Continue after questions are resolved.

### Review mode

Review mode is read-only. It inspects an existing specification, implementation, or diff; runs safe verification where permitted; and reports correctness, security, performance, and maintainability findings without applying changes.

### Future modes

- Autonomous: implement a bounded, accepted specification with minimal interruption.
- Collaborative: edit interactively while asking for input only at material decision points.
- Research: gather and compare evidence without implementing.

The first release does not need every mode. Teaching and review are the initial candidates.

## Skills and runtime adapters

The canonical procedure should exist once, preferably in a portable Agent Skills layout such as `.agents/skills/`. Runtime-specific adapters should remain thin.

Example:

```text
.agents/skills/
├── checkpoint-context/
├── explain-change/
└── review-diff/

.opencode/agents/
├── teaching.md
└── review.md
```

The skill contains the reusable procedure. The OpenCode agent definition supplies persistent mode, model selection, and tool permissions. Equivalent adapters may be added for other runtimes without copying the full procedure.

## Interactive command runbook

The harness should expose a command catalog that is both human-readable and agent-usable.

Each command definition should record:

- Stable command identifier and syntax.
- Plain-language purpose.
- When to use it and when not to use it.
- Preconditions.
- Positional arguments, options, defaults, and environment variables.
- Files and external state it may read or modify.
- Permission and approval implications.
- Output schema and exit codes.
- Common examples.
- Expected failure modes and recovery steps.
- Related commands and the workflow stage in which it belongs.
- Runtime and version compatibility.
- Whether it is deterministic, networked, destructive, or experimental.

The same canonical definition should support multiple views:

```text
harness <command> --help
    Concise terminal help

harness explain <command>
    Detailed human runbook entry

harness schema <command> --json
    Machine-readable contract for agents and integrations

harness docs build
    Generated static Markdown or HTML reference

harness docs serve
    Local searchable and interactive command explorer
```

The interactive explorer may eventually provide:

- Search and filtering by workflow stage, risk, runtime, or workload profile.
- Copyable command construction from validated fields.
- Examples with explanations.
- Input and output schemas.
- Side-effect and permission warnings.
- Links to specifications, decisions, skills, and evaluation evidence.
- Version badges and deprecation notices.
- Dry-run output where a command supports it.

The initial release does not need a polished web interface. It does need structured command metadata and generated Markdown so an interactive UI can be added without redesigning the CLI.

The runbook must not expose API keys, environment values, private paths, or captured command output containing secrets. Examples should use placeholders, and generated documentation should classify sensitive inputs explicitly.

## Compaction foundations

### Native OpenCode summarization

OpenCode currently supports automatic compaction that summarizes earlier conversation while retaining a recent exact window. Its documented defaults retain approximately 15,000 recent tokens and reserve a buffer near the context limit. Later compactions update an existing summary using conversation since the prior checkpoint.

OpenCode sends the full conversation to the summary request so the compaction request can reuse the normal prompt cache when the provider supports it. After compaction, however, the conversation prefix has changed. The new compacted context must be prefetched and can then become the stable cached prefix for subsequent turns.

Research source: <https://dev.opencode.ai/v2/docs/compaction/>

### CliffCompaction

CliffCompaction is a deterministic, scaffold-agnostic strategy designed for long-horizon coding agents. Rather than asking an LLM to rewrite history into prose, it retains selected information verbatim and removes recoverable bulk.

Core mechanics described by the paper:

- Let context grow unchanged until a configured token threshold.
- Preserve the system prompt and original task.
- Keep a configured number of recent turns unchanged.
- Drop older tool results above a size threshold; the reference implementation uses 500 characters.
- Retain concise tool results such as exit codes and small search matches.
- Reduce old tool calls to signatures containing the tool name and essential arguments.
- Truncate old reasoning; the reference algorithm uses 300 characters.
- Never compact a previous compaction into the next one.
- At a later cliff, discard the old compacted block and compact only the live conversation accumulated since it.

This trades historical recall for precision. It avoids recursive summary drift and changes the prompt only at occasional cliffs, allowing long cache-reuse segments between compactions.

The paper reports that, at matched context budgets, CliffCompaction maintained or improved performance while reducing cost across Terminal-Bench and SWE-bench Verified. Of particular relevance, it reports improved Terminal-Bench 2.1 results using GLM-5.3 Flash through Claude Code at an approximately 45K peak context compared with both matched native compaction and the default larger context.

Research source: [CliffCompaction: Cost-Efficient Compaction for Long-Horizon Coding Agents](https://arxiv.org/html/2609.26779v1)

### Proposed hybrid strategy

The leading hypothesis is to combine:

```text
CliffCompaction
    High-precision recent conversational context

Durable repository checkpoint
    Explicit accepted decisions and verified task state

Source files and Git
    Canonical implementation history

Content-addressed repository index
    Cheap recovery of previously analyzed code
```

This is a hypothesis, not yet a decision. It must be evaluated against native OpenCode summarization and unmodified full-context behavior.

> **Cache warning:** Every compaction event necessarily changes the active context and invalidates at least the suffix of the existing prompt/KV cache. A hybrid checkpoint strategy must not continuously rewrite or reinject changing state into the prompt. Checkpoints should be stable between material events, and compaction should be infrequent enough that the smaller replacement prefix earns back its re-prefill cost over later turns.

### Durable checkpoints

A checkpoint should update only after material events, for example:

- A decision is accepted.
- A coherent implementation milestone is verified.
- A handoff is about to occur.
- A session is ending incomplete.
- Compaction is imminent, if a reliable hook exists.

It should not update on every turn. Constant rewrites would create noisy diffs, spend tokens, and repeatedly perturb prompt prefixes if automatically injected.

Candidate checkpoint fields:

```text
Objective
Accepted decisions
Current implementation status
Files changed
Verification and exact outcomes
Known failures and risks
Exact next action
```

## Prompt-cache and content-cache distinctions

> **Critical design constraint:** A lower token count does not guarantee a lower total cost. Frequent compaction, sliding windows, reordered instructions, changing checkpoint text, or repeated reinjection of generated summaries can destroy prefix-cache continuity. This can convert previously discounted cached-input tokens into more expensive uncached-input tokens and add latency through repeated prefills.

The harness must distinguish:

- Operating-system cache: reuses file bytes locally.
- Provider prompt cache: reuses an identical request prefix or common prefix.
- Model KV cache: backend representation underlying efficient continuation.
- Repository-analysis cache: reuses derived facts about unchanged Git blobs.
- Retrieval cache: reuses results for repeated or equivalent searches.

Re-reading identical file contents later does not automatically imply a provider prompt-cache hit. Prompt caching is normally positional and prefix-sensitive, not an arbitrary content-addressed store.

Any compaction changes the active prompt and invalidates cache after the last common prefix. Cliff-style strategies seek to amortize that reset by compacting infrequently and shrinking the new prefix substantially.

For a context-management strategy to be considered successful, it must demonstrate that:

```text
cost saved by processing a smaller context over later turns
    >
cost of compaction + cache invalidation + replacement-context prefill
```

This break-even point depends on the provider's cached-input discount, model, context length, number of post-compaction turns, and whether the provider actually honors caching for the request pattern used by the harness.

The harness must never infer a cache hit merely because identical file text appears again. Provider caching is generally sensitive to the ordered request prefix. Repository content-addressing and provider prompt caching solve different problems and require different metrics.

## Content-addressed repository indexing

Embedding-based retrieval is not an initial requirement for source code. The source-code study of eleven coding harnesses found that none used vector embeddings for code retrieval; production systems favored deterministic retrieval and hand-built loops.

The initial indexing direction is therefore:

```text
Git blob hash
    -> parser/analyzer version
    -> symbols
    -> imports and dependencies
    -> test relationships
    -> concise derived summary
```

When the blob hash changes, only that file's derived record becomes stale. If the analyzer changes, affected records are invalidated by analyzer version.

Questions still requiring investigation:

- Whether Tree-sitter, language-server data, or language-native parsers should be primary.
- Whether summaries are generated eagerly or only after repeated access.
- Whether cache entries belong under Git's common directory, a user cache, or a project service.
- How multiple worktrees safely share the index.
- Whether documentation and notes should use a separate semantic index.

## Cross-agent coordination

Cross-agent coordination is desirable but not an initial priority. Native runtimes already support some read delegation and subagent work. The larger unresolved problem is live state shared across worktrees.

A future coordination layer may track:

- Agent identity and runtime.
- Repository and worktree.
- Branch and base revision.
- Task ownership and dependencies.
- Current status and heartbeat.
- Structured messages and handoffs.
- Verification evidence.

Transient coordination should not be committed as normal project history. Durable decisions and completed outcomes should be promoted into repository documentation.

## Evaluation-first methodology

Evaluation is a first-class harness execution mode, not merely a directory of prompts or an agent skill.

An evaluation must freeze and record:

- Harness version and Git commit.
- Target repository revision.
- Runtime and runtime version.
- Provider and model.
- Agent instructions and available skills.
- Tool permissions and environment restrictions.
- Compaction strategy and threshold.
- Recent-context retention.
- Interaction mode.
- Timeouts and network policy.
- Benchmark version and task identifiers.
- Seeds or replicate identifiers where supported.

### Evaluation levels

#### Level 1: Deterministic trace evaluation

Apply compaction and context mechanisms to recorded trajectories without asking a model to solve the task again.

Measure:

- Tokens before and after.
- Directive retention.
- Decision retention.
- Recoverability of tool calls and files.
- Number of prompt rewrites and implied cache resets.
- Runtime and deterministic reproducibility.

#### Level 2: Local workflow evaluations

Use small controlled repositories to test:

- Resumption after compaction.
- Retention of an architectural constraint.
- Recovery of a discarded file read.
- Continuation from a verified checkpoint.
- Detection that a file changed after an earlier analysis.
- Avoidance of a previously failed approach.
- Accurate Git, branch, worktree, and PR awareness.
- Teaching-mode behavior and human comprehension.

#### Level 3: External harness benchmarks

Initial adapters may target:

- Terminal-Bench.
- SWE-bench Verified.
- KernelBench later, if continual optimization becomes relevant.

External runs are slower and more expensive. They should follow deterministic and local regression tests rather than replace them.

### Core metrics

- Task success and pass@1.
- Input, cached-input, uncached-input, and output tokens.
- Reported or estimated cost.
- Wall-clock latency.
- Peak and mean context size.
- Compaction count and tokens removed.
- Prompt-prefix changes and estimated cache resets.
- Cached-to-uncached token conversion after context mutation.
- Replacement-context prefill cost and latency.
- Number of subsequent turns required to break even after each compaction.
- Repeated tool calls and unnecessary file rereads.
- Constraints retained or lost.
- Incorrect assumptions introduced.
- Verification commands and outcomes.
- Human corrections required.

Teaching-mode evaluation should separately measure whether the developer could follow and explain the resulting implementation.

### Protecting against benchmark overfitting

Use separate collections:

- Development scenarios for designing the feature.
- A regression suite run on every harness change.
- Holdout scenarios used only before policy promotion.
- External benchmarks used periodically to test generalization.

Eval mode must disable autonomous changes to canonical policy.

## Harness-policy evolution

Research distinguishes the model policy from the harness policy.

- Model policy: the learned model behavior, potentially updated through training or reinforcement learning.
- Harness policy: prompts, tools, middleware, memory, permissions, orchestration, and execution rules surrounding the model.

The Self-HPO work alternates between a harness step, where a model proposes harness candidates from observed failures, and a policy step, where the underlying model is updated through reinforcement learning. This project initially keeps provider models fixed and experiments only with the harness.

The Agentic Harness Engineering work proposes three forms of observability:

- Component observability: editable harness components are explicit and revertible.
- Experience observability: large traces are distilled into evidence an improvement process can inspect.
- Decision observability: every edit declares a prediction that is later compared with measured outcomes.

This project adopts decision observability as a design principle. It does not yet adopt autonomous harness evolution.

## Prior research

### Primary harness research

1. [Self-Evolving Coding Agents via Harness-Policy Optimization](https://arxiv.org/abs/2610.22791)
   - Alternates harness proposal with model-policy reinforcement learning.
   - Demonstrates that harness and model policy can improve one another.
   - Motivates failure-driven, testable harness proposals.

2. [Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents](https://arxiv.org/abs/2609.00006)
   - Studies eleven production coding harnesses plus a meta-harness.
   - Defines recurring harness subsystems and design patterns.
   - Reports deterministic retrieval rather than embedding-based code retrieval across the audited systems.

3. [Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses](https://arxiv.org/abs/2604.25850)
   - Frames harness edits as observable, falsifiable contracts.
   - Attributes much of the measured improvement to tools, middleware, and long-term memory rather than prompt prose alone.

4. [CliffCompaction: Cost-Efficient Compaction for Long-Horizon Coding Agents](https://arxiv.org/html/2609.26779v1)
   - Uses deterministic dropping and truncation rather than recursive LLM summaries.
   - Prioritizes compaction precision and cache-efficient growth segments.
   - Supplies benchmark results and an open-source scaffold-agnostic proxy implementation.

### Adjacent context and memory research to evaluate

- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
- [A-MEM: Agentic Memory for LLM Agents](https://arxiv.org/abs/2502.12110)
- [LongLLMLingua](https://arxiv.org/abs/2310.06839)
- [LLMLingua-2](https://arxiv.org/abs/2403.12968)

These are research inputs, not adopted dependencies or settled designs.

## Proposed implementation phases

### Phase 1: Evaluation contract and baseline

- Define the run manifest, metrics, result format, and comparison method.
- Capture baseline OpenCode behavior on representative tasks.
- Create deterministic compaction traces and local resumption tasks.
- Define the initial command metadata schema and generate the first Markdown runbook entries alongside the evaluation CLI.

### Phase 2: Interaction and repository awareness

- Add teaching and read-only review modes.
- Enforce direct file editing and editor-oriented references.
- Surface repository, worktree, branch, base revision, dirty files, and PR state.

### Phase 3: Compaction experiments

- Reproduce native OpenCode summarization behavior.
- Implement or integrate CliffCompaction under a compatible license.
- Test the hybrid durable-checkpoint approach.
- Compare context thresholds and retention settings.

### Phase 4: Content-addressed repository index

- Index files by Git blob hash and analyzer version.
- Add symbols, imports, test relationships, and selective summaries.
- Measure reread reduction and task impact.

### Phase 5: Cross-agent coordination

- Design shared transient state across worktrees.
- Add task ownership, dependencies, messaging, and handoffs.
- Promote only durable outcomes into repository history.

### Phase 6: Controlled harness evolution

- Generate policy proposals from observed failures.
- Require predictions, isolated evaluation, and regression checks.
- Keep human approval as the promotion boundary.

## Current decisions

- The harness will live in its own reusable repository.
- It will initialize and validate target repositories through a CLI.
- Evals are a first-class mode and the first implementation priority.
- The command runbook is generated from canonical CLI metadata and evolves with the implementation.
- Teaching and review are the first interaction modes to design.
- Code should be edited directly in the workspace and inspected through the editor and Git diff.
- Compaction will be evaluated rather than selected by intuition.
- Cache continuity and total task cost are first-class acceptance criteria for every compaction strategy.
- CliffCompaction is the first serious alternative to native summarization.
- Embedding-based source-code retrieval is out of initial scope.
- Content-addressed repository indexing remains a medium-priority research direction.
- Cross-agent coordination is deferred until the single-agent lifecycle is reliable.
- Canonical harness policy cannot modify itself autonomously.

## Open questions

1. What representative tasks should form the initial local evaluation suite?
2. Which compaction thresholds should be compared first?
3. What information must survive compaction verbatim versus through a repository checkpoint?
4. Can OpenCode expose reliable cached-token and uncached-token usage for Z.AI Coding Plan runs?
5. Should CliffCompaction be integrated through an API proxy, a runtime plugin, or a harness-owned transcript transformer?
6. How should teaching-mode human understanding be measured without making evaluation overly subjective?
7. Where should shared content-addressed indexes live across worktrees?
8. Which rules belong in portable skills versus runtime-specific agent configuration?
9. What is the smallest useful CLI surface for the first release?
10. What licensing and attribution requirements apply to any reused CliffCompaction implementation?
11. Should the interactive command explorer be a generated static site, a local server, a terminal UI, or multiple projections of the same schema?

## Non-goals for the first release

- Reimplementing OpenCode, Codex, or Superset.
- Training or reinforcement-learning a foundation model.
- Building a learned model router.
- Semantic vector search over source code.
- Fully autonomous multi-agent project management.
- Autonomous modification or promotion of canonical harness policy.
- Optimizing for every workload before one end-to-end workflow is validated.
