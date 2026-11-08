# Local knowledge retrieval, code norms, and graph-assisted RAG

## Status

High-priority research and implementation track. Build the first vertical slice immediately
after the CliffCompaction vertical slice. This note records evidence and a leading design
hypothesis; it does not promote the hypothesis to canonical harness policy.

## Core problem

Development agents need project rules, language conventions, architectural decisions, source
relationships, and sometimes personal research notes. Injecting all of that material into every
request consumes context, weakens prompt-cache efficiency, and can bury the relevant instruction.
Retrieving only relevant material saves context, but a missed retrieval can cause the agent to
forget a required rule.

The harness therefore needs to answer:

> How can a smaller model receive the minimum sufficient knowledge for the current task without
> making correctness depend on unreliable, model-initiated retrieval?

## Scope boundaries

Three knowledge domains should share an interface without sharing storage or policy by default:

1. **Code norms** — portable rules and examples for languages, task types, and development areas.
2. **Repository knowledge** — symbols, files, dependencies, tests, and other content-addressed
   facts about a codebase.
3. **Personal notes** — private Obsidian notes, links, tags, concepts, and project research.

The harness may own the runtime-neutral tool contract and adapters. Personal source material and
its credentials or paths remain local, ignored, and explicitly enabled. Repository retrieval and
personal-note retrieval may require different ranking methods even when they implement the same
tool contract.

## Research evidence

### Long input is not equivalent to usable context

- [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/) found that models often use
  relevant information less reliably when it appears in the middle of a long input.
- [Context Length Alone Hurts LLM Performance Despite Perfect Retrieval](https://aclanthology.org/2025.findings-emnlp.1264/)
  reported degradation across math, question-answering, and coding tasks even when relevant
  evidence was perfectly retrieved and inputs remained within advertised context limits.
- [Benchmarking Long-Context Language Models on Long Code Understanding](https://aclanthology.org/2025.acl-long.1324/)
  reported substantial degradation beyond 32K tokens and identified inter-code-unit relationships
  as particularly difficult.
- [Sense and Sensitivity](https://aclanthology.org/2026.acl-long.19/) distinguished lexical from
  semantic recall and found strong positional degradation for semantic code understanding.

These results support reducing irrelevant context. They do not prove that retrieval always beats
full context for code norms.

### Retrieval helps only when it retrieves and presents the right evidence

- [RepoCoder](https://arxiv.org/abs/2303.12570) showed that iterative repository retrieval can
  improve repository-level code completion relative to in-file and single-pass retrieval
  baselines.
- [CodeRAG-Bench](https://aclanthology.org/2025.findings-naacl.176/) found that high-quality
  retrieved context improves code generation, while also finding that retrievers often fail to
  fetch useful context and generators sometimes fail to use it.
- [Retrieval Augmented Generation or Long-Context LLMs?](https://arxiv.org/abs/2407.16833)
  found long-context prompting stronger than the evaluated RAG systems on its tasks, while a
  hybrid routing approach recovered much of the quality with lower token use.
- [Agent Retrieval Bench](https://arxiv.org/abs/2607.24882) is a recent preprint evaluating
  lexical retrieval, repository maps, embeddings, and logged agent selection. It reports that no
  single retrieval family dominates and that logged trajectories can miss needed files. Treat
  these results as a research lead until independently reproduced.

The evidence argues against both extremes: neither one giant context nor retrieval-only policy is
a safe universal default.

### Graph retrieval is promising but not yet the default

- [RANGER](https://arxiv.org/abs/2509.25257) is a preprint combining a repository knowledge graph,
  embeddings, graph queries, and guided exploration across code-retrieval tasks.
- [Agentic Context Engineering](https://arxiv.org/abs/2510.04618) treats context as a structured,
  evolving playbook and reports benefits from incremental generation, reflection, and curation.

These works motivate typed relationships and structured context, but they do not establish that a
graph database or graph expansion is the best first implementation for code norms. The harness
should test graph expansion against simpler deterministic and lexical baselines.

## Leading design hypothesis

Use a layered knowledge policy:

```text
Tier 0: always-loaded invariants
    Small mandatory rules: safety, credentials, approvals, validation, canonical policy.

Tier 1: deterministic selection
    The harness selects applicable norms from path, language, task type, and repository metadata.

Tier 2: on-demand retrieval
    The model retrieves detailed examples, explanations, prior decisions, and supporting notes.

Tier 3: bounded graph expansion
    Typed neighboring nodes are added only when their relationship and token budget justify it.
```

Required behavior must not depend solely on the model remembering to search. A missing required
Tier 0 or Tier 1 rule should be visible as a harness failure, not silently treated as an empty
retrieval result.

### Accepted invariant boundary

Security and other critical operating invariants are always ingested and non-negotiable. They do
not depend on semantic search, graph traversal, model-initiated tool use, or retrieval confidence.
The initial always-loaded set includes credential and private-data handling, approval and
permission boundaries, destructive-action safeguards, canonical-policy immutability, and required
verification behavior. This set must remain small, stable, ordered, and auditable so it protects
behavior without recreating the oversized-context problem.

Retrieval may add stricter or more specific guidance for a task, but it may not weaken, replace, or
silently contradict an always-loaded invariant.

## Norm representation

Begin with structured Markdown rather than a dedicated graph database:

```yaml
id: python.error-handling
status: active
priority: required
applies_to:
  languages: [python]
  paths: ["src/**/*.py"]
  tasks: [implementation, review]
relations:
  requires: [backend.api-errors]
  conflicts: []
  examples: [python.error-handling.examples]
```

Typed relationships should have explicit loading behavior:

- `requires` — include with the selected node.
- `conflicts` — surface for resolution.
- `supersedes` — exclude or mark the stale node.
- `example_of` — retrieve only when detail is useful.
- `related_to` — optional, budgeted expansion.

This metadata already defines a graph. A different storage engine can materialize it later without
changing the canonical norm format.

## Runtime-neutral tool surface

The canonical tool registry should eventually define a small stable interface:

```text
knowledge.search(query, source, filters, limit)
knowledge.get(source, document_id, section)
knowledge.neighbors(source, node_id, relations, depth, limit)
knowledge.resolve(task, paths, languages)
```

`knowledge.resolve` is deterministic selection, not semantic search. The OpenCode plugin is the
first adapter; MCP may later expose the same contract to other runtimes. Tool names, schemas, and
ordering should remain stable because changing the tool prefix can damage provider prompt-cache
continuity.

Results should be bounded and cite stable document or norm identifiers. Large content should be
returned through a durable reference or a follow-up `knowledge.get`, not copied wholesale into the
conversation.

## Initial local implementation

Start with a local SQLite store rather than a network service or graph database:

```text
documents       source identity, path, content hash, metadata
chunks          bounded searchable passages
edges           typed relationships between nodes
source_hashes   incremental invalidation state
retrieval_events query, candidates, selected results, and outcome labels
```

SQLite full-text search plus deterministic filters and adjacency queries is sufficient for the
first lexical-plus-graph baseline. Add embeddings only after an evaluation identifies misses that
lexical search and typed relationships cannot address.

The content hash identifies unchanged source material. Analyzer, chunker, and embedding versions
must also participate in cache invalidation so derived records are never assumed valid after their
logic changes.

## Tokenization and local models

- Tool registration and graph traversal do not require a tokenizer.
- A local tokenizer may estimate retrieval and Cliff budgets, but provider-reported usage remains
  authoritative unless the exact served model tokenizer is verified.
- An embedding model uses its own tokenizer and can run locally when embeddings are introduced.
- A local summarization model is optional and should not be required for the first retrieval path.
- Generated summaries are derived data; source notes and norms remain canonical.

## Interaction with CliffCompaction and prompt caching

CliffCompaction and knowledge retrieval solve different problems:

- Cliff decides which prior conversational information remains model-visible.
- Retrieval decides which external knowledge enters the live conversation.

Retrieved knowledge should normally arrive as a tool result at the live tail. Continuously
rewriting early system instructions with changing retrieved content would invalidate more of the
prompt prefix. A selected norm bundle may be frozen for a coherent task segment and identified by
an ordered manifest and content hash.

When Cliff later drops a large retrieval result, it should preserve a compact tool signature and
stable document identifiers so the agent can recover the material with another call.

## Privacy boundary

Local indexing does not by itself keep retrieved content private. Once a hosted model receives a
retrieval result, that content has crossed the provider boundary.

Personal-note sources therefore require:

- local, ignored path configuration;
- per-source enablement and sensitivity labels;
- bounded excerpts rather than whole notes;
- redaction or approval for sensitive collections;
- logs that default to hashes and metadata rather than raw content;
- no committed note text, embeddings, private paths, or retrieval traces.

## Post-Cliff minimum viable vertical slice

Implement and evaluate this sequence immediately after the CliffCompaction vertical slice:

1. Define the canonical `knowledge.search`, `knowledge.get`, and `knowledge.resolve` schemas.
2. Index structured Markdown norms with content hashes in local SQLite.
3. Add lexical search, deterministic scope filters, and one-hop typed graph expansion.
4. Expose the tools through the managed OpenCode plugin.
5. Add an isolated Obsidian source adapter using links, tags, folders, and note metadata.
6. Record bounded retrieval events and explicit source citations.
7. Evaluate before adding embeddings, a graph database, or model-generated summaries.

Candidate CLI surface:

```text
harness knowledge index
harness knowledge status
harness knowledge search <query>
harness knowledge explain <result-id>
```

## Evaluation contract

Compare:

1. One large norms Markdown file injected in full.
2. Small invariant core plus model-initiated retrieval.
3. Small invariant core plus deterministic selection and retrieval.
4. The third condition plus bounded graph expansion.

Evaluate separately on frontier and smaller workhorse models. Measure:

- task success;
- required-rule recall and violations;
- irrelevant and total retrieved tokens;
- retrieval precision, recall, and abstention quality;
- correct first tool selection and repair turns;
- latency and local resource use;
- prompt-cache discontinuity;
- post-Cliff recovery of previously retrieved knowledge;
- whether cited sources actually support the agent's action.

The leading prediction is that deterministic selection plus retrieval will outperform both a giant
always-loaded file and model-initiated retrieval alone for smaller models. Graph expansion should
be promoted only if it improves rule recall or task success without excessive noise and latency.

## Failure modes and safeguards

- **The model forgets to search:** deterministically resolve required norms before work begins.
- **Retriever misses a required norm:** fail visibly for required scope mappings; retain a small
  always-loaded invariant set.
- **Graph expansion adds noise:** use typed edges, shallow depth, and explicit token/result limits.
- **Stale derived data:** invalidate on source hash or analyzer-version changes.
- **Conflicting norms:** return both with priority and supersession metadata; require resolution.
- **Changing retrieval harms caching:** freeze ordered bundles within a task segment and append
  on-demand results at the live tail.
- **Private notes reach a hosted model:** classify sources and require explicit enablement or
  approval for sensitive material.
- **Observability becomes a second transcript:** record bounded metadata and hashes by default.

## Open questions

1. What is the minimum always-loaded invariant set?
2. Which repository signals determine the Tier 1 norm bundle?
3. Should selected norm bundles persist for a task, session, or worktree milestone?
4. What retrieval misses occur on the intended smaller OpenCode Go models?
5. Which Obsidian link and metadata types should become graph edges?
6. When does semantic embedding retrieval add enough value to justify its local cost?
7. Should personal-note retrieval require per-call approval before content reaches a hosted model?
8. How should retrieval evidence be labeled so it can train or evaluate later decision models?
