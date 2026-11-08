# Proposed coding-norm library

Status: Proposal for review
Schema: `schemas/norm.schema.json`

## Purpose

The norm library is a runtime-neutral way to author small, independently selectable coding
rules. It is intended to replace the pattern of injecting one large norms document into every
request. Runtime adapters may project selected norms into OpenCode or another agent runtime, but
the authored Markdown remains the canonical source.

This document proposes a contract; it does not promote the example norms to canonical harness
policy.

## File format

Each norm is a Markdown file with TOML frontmatter delimited by `+++`:

```markdown
+++
schema_version = 1
id = "backend.python.api_design"
version = 1
title = "Python API design"
summary = "A short description of the norm's purpose."
status = "draft"
priority = "advisory"
delivery = "scoped"

[scope]
areas = ["backend"]
languages = ["python"]
paths = ["**/*.py"]
tasks = ["implementation", "review"]

[[relations]]
type = "related_to"
target = "backend.python.testing"

[provenance]
kind = "repository"
source = "project proposal"
owner = "project-maintainers"
+++

## Rule

The concise rule text.

## Rationale

Why the rule exists and what failure it prevents.
```

TOML was selected for the first implementation because Python 3.11 can parse it with `tomllib`;
the harness does not need a new YAML dependency. Field names and list order remain stable so
runtime projections and cache-sensitive prompts can be deterministic.

## Metadata contract

- `schema_version`: format version; currently exactly `1`.
- `id`: stable lowercase identity. Moving or renaming a file does not change its ID.
- `version`: positive revision number for the norm itself.
- `title` and `summary`: bounded human and retrieval labels.
- `status`: `draft`, `active`, or `deprecated`. Normal resolution excludes drafts and deprecated
  norms unless the caller opts in.
- `priority`: `required` or `advisory`. Priority controls enforcement after a norm is selected; it
  does not decide whether the norm is selected.
- `delivery`: `always`, `scoped`, or `on_demand`.
- `scope`: lists of `areas`, `languages`, `paths`, and `tasks`. Values within one dimension are OR;
  populated dimensions are combined with AND.
- `relations`: typed links to stable norm IDs: `requires`, `conflicts`, `supersedes`, `example_of`,
  or `related_to`.
- `provenance`: source class and source reference, with optional owner and review date. Provenance
  records where guidance came from; it does not automatically grant authority.

Every relation target must exist in the same loaded library. Duplicate IDs and self-relations are
invalid. A `requires` edge identifies another norm that must be included when the source norm is
selected; a runtime projection must not silently emit the source without its required target.

## Bounded Markdown body

The body contains `## Rule` and `## Rationale`, followed optionally by `## Examples` and
`## Failure modes`, in that order. Arbitrary preambles and other headings are rejected.

The initial loader bounds the body to 8,000 characters and each section to a smaller fixed limit.
These limits make an individual norm inspectable and prevent a single file from recreating the
huge-document ingestion problem. They are implementation guardrails, not evidence-backed optimal
token budgets, and should be tuned through evaluation.

## Deterministic selection

For a scoped norm, every populated selector dimension must match the request context. For example,
a norm with `areas = ["backend"]`, `languages = ["python"]`, and
`tasks = ["implementation"]` matches only when all three values are supplied and match. Path
selectors use case-sensitive glob matching with `/` separators.

Resolution returns norms ordered by stable ID and expands `requires` relations. It does not use
embeddings or model judgment. This creates an auditable baseline before semantic or graph-assisted
retrieval is evaluated.

## Ingestion-cost boundary

The three delivery classes serve different context budgets:

1. `always`: a very small, stable set of non-negotiable safety and security invariants. An
   always-delivered norm must be `required`. This layer must not become a general style guide.
2. `scoped`: rules selected deterministically from area, language, path, and task metadata. These
   are injected only when applicable, without relying on the model to remember a search call.
3. `on_demand`: detailed examples or specialized guidance exposed through retrieval tools and
   omitted from ordinary context.

The harness should measure selected bytes/tokens, required-rule recall, irrelevant-rule rate, rule
violations, and task success against the large-file baseline. Smaller input alone is not proof of
better behavior.

Always-loaded invariants remain separate from Cliff compaction and retrieval. They are stable
instructions that must survive every context projection. Retrieval failures must not be able to
remove them, and retrieved content must never override them.

There is no evidence-backed universal token count for the always-loaded layer. The initial
constraint is therefore operational: include only invariants whose omission could make an action
unsafe or unauthorized, report their aggregate projected bytes/tokens, and require review whenever
that aggregate grows. A style preference or detailed implementation recipe is not an invariant.

## Provenance and authority

Repository policy, upstream documentation, personal notes, and external material must remain
distinguishable. A Stack Overflow post or arbitrary note can be useful evidence, but it cannot
silently become required policy. Promotion from draft or advisory material to active required
policy requires human review outside this loader.

## Scaffold layout

The initial hierarchy demonstrates composition without claiming a mature norm corpus:

```text
norms/
└── backend/
    └── python/
        ├── api-design.md
        ├── background-jobs.md
        └── testing.md
```

All three examples are draft and advisory. They are authoring scaffolds, not accepted engineering
rules.

## Portable vendoring

The repository-root `norms/` tree is the canonical shared library bundled into release wheels.
`harness init` copies that complete tree into a target repository. By default its generated copy
is registered in the clone-local `.git/info/exclude`; `--tracked` leaves it visible for project
commit. Either way, the copy is intentionally vendored: after initialization it belongs to the
target and may be reviewed, activated, revised, or removed there without changing the harness
source library.

Initialization never overwrites an existing target norm. This prevents a harness upgrade from
silently changing project policy. A future explicit sync command will need a three-way or
fingerprint-aware review flow; rerunning `init` is not a synchronization mechanism.

`README.md` and `INDEX.md` are reserved navigation filenames. Every other Markdown file below a
norm root is treated as a norm and must validate; a missing frontmatter block is therefore an error
rather than a silently skipped rule.

## Research-efficiency audit

Audit date: 2026-11-03. Source findings below are separated from harness inferences. Preprints are
treated as directional evidence rather than settled results.

### Evidence: minimize irrelevant standing instructions

- Du et al. found substantial degradation from longer input on math, QA, and coding even with
  perfect retrieval and within supported context lengths. This supports minimizing total context,
  not merely improving search accuracy. ([EMNLP Findings 2025](https://aclanthology.org/2025.findings-emnlp.1264/))
- Gloaguen et al. tested multiple coding agents, including GPT-5.1 Mini and Qwen3-30B-Coder
  configurations, and found repository context files increased cost by roughly 20% without a
  statistically significant task-success gain in their tested settings. Developer files were
  shorter than generated files, and the authors recommend minimal requirements. The result does
  not show that every project rule is harmful, but it argues against a generated catch-all file.
  ([2026 workshop paper and preprint](https://arxiv.org/abs/2602.11988))
- A small 2026 study across five Python libraries and two models found that more instruction
  categories did not reliably improve generated code and recommends selecting instructions for the
  current objective. Its limited task and repository sample makes this supporting, not conclusive,
  evidence. ([Polandra et al. 2026](https://arxiv.org/abs/2610.21421))
- A controlled 2026 synthetic study across five models found instruction adherence decayed as rule
  count increased and perfect-response rate reached zero by 80 simultaneous rules in every tested
  format. It does not establish a safe coding-agent cutoff, but it is further evidence against an
  unbounded invariant list. ([Eliav 2026](https://arxiv.org/abs/2607.19257))

**Harness inference:** retain a tiny always-loaded safety boundary and select ordinary engineering
rules by task and scope. Do not establish a fixed invariant token budget until the intended models
are evaluated; record aggregate projected size and rule count so growth is visible.

### Evidence: one-level progressive disclosure

The Agent Skills specification describes discovery metadata followed by full instructions only on
activation and resources only during execution.
([Agent Skills overview](https://github.com/agentskills/agentskills/blob/main/docs/home.mdx))
A controlled 2026 preprint tested GPT-5.4 Mini, Qwen3.6-27B, and Claude Haiku 4.5 and found
one-level progressive disclosure increasingly useful as a long-document corpus grew, while a
second routing level never improved its evaluated tasks and sometimes reduced accuracy. The study
concerns books, not coding norms, so it supports the loading shape rather than proving task
performance here.
([He et al. 2026](https://arxiv.org/abs/2607.17598))

**Harness inference:** use one local index-to-content hop:

```text
validated local index
    id + title + bounded summary + selectors + relation IDs
            |
            | deterministic resolution or bounded search
            v
exact norm body
    Rule + Rationale; optional detail only when requested
```

The index remains local; its complete contents are not an always-visible model catalog. The
frontmatter is indexing and validation data, and a runtime must not inject the TOML block into the
model prompt. A compact projection should contain stable identity/version/priority plus the body
sections needed for the current task. For on-demand material, the model should first receive only a
bounded result list, then fetch the exact selected norm in one additional step. Recursive
directory-by-directory routing is out of scope for the initial design.

### Evidence: deterministic retrieval before graph expansion

Agent Retrieval Bench reports that no retrieval family dominates repository-context acquisition;
logged agent trajectories missed every gold file on 27--35% of samples, while semantic and
structural methods were complementary. ([2026 preprint](https://arxiv.org/abs/2607.24882))
Graph retrieval can improve multi-hop reasoning on explicitly networked documents, but the evidence
comes from graph-reasoning and QA benchmarks rather than coding-policy selection.
([GRAG, NAACL Findings 2025](https://aclanthology.org/2025.findings-naacl.232/))

**Harness inference:** correctness-critical norms must not depend on model-initiated search.
Resolve them from explicit area/language/path/task selectors and expand only `requires` edges.
`related_to` and `example_of` are candidates for bounded retrieval, not automatic context
expansion. `conflicts` and `supersedes` must be surfaced for deterministic resolution before a
runtime projection is emitted. Arbitrary nearest-neighbor traversal would risk rebuilding the giant
document through graph expansion.

A required norm can still be absent from the corpus entirely; no retriever can find an undeclared
rule. Before policy promotion, a separate repository coverage manifest should declare which
required norm IDs are expected for known scopes. Missing expected IDs must fail visibly. This is a
design safeguard inferred from retrieval failure evidence, not functionality implemented by the
current loader.

### Chunk granularity and hierarchy

A 2025 code-RAG preprint found that moderate 32--64-line code chunks worked best at small context
budgets in its completion experiments, while whole files became competitive at larger budgets. It
also found that the best granularity varied with task and budget.
([Galimzyanov et al. 2025](https://arxiv.org/abs/2510.20609)) This result should not be converted
directly into a line limit for prose rules.

**Harness inference:** the unit for a norm is one independently applicable rule, not an arbitrary
line window. Keep `Rule` and `Rationale` together because separating the reason can make the rule
harder to interpret. Move lengthy examples into a separate `on_demand` norm linked with
`example_of`. The existing per-section and total character ceilings are safety guardrails, not
optimal chunk sizes, and remain unchanged until norm-specific evaluations justify tighter limits.

The `backend/python/{api-design,background-jobs,testing}` files are an appropriate authoring
hierarchy because the three topics have different task applicability. Directory ancestry does not
cause ingestion, and `related_to` links do not auto-expand. If two files always resolve together
and neither is useful alone, they should usually become one norm; if a file accumulates multiple
independently selectable rules, it should be split.

### Stable ordering and prompt-cache behavior

OpenAI's prompt-caching documentation states that cache reuse depends on a matching prefix and
recommends stable instructions, tool definitions, and append-only conversation history. It also
warns that compaction and prefix rewrites can reset reuse. Provider behavior varies, so this is a
mechanism to measure rather than an OpenCode Go guarantee.
([OpenAI prompt-caching guide](https://developers.openai.com/api/docs/guides/prompt-caching))

**Harness inference:** normalized runtime bundles must sort norms by stable ID and keep field and
section order fixed. Freeze a selected bundle for a coherent task segment. Do not rewrite the
standing prefix every time search results change; append on-demand retrieval results at the live
tail. When scope changes require a new bundle, record the old/new bundle hashes and provider cache
metrics so the reset cost can be evaluated.

### Corpus-growth safeguards

The initial implementation deliberately retains these constraints:

- no embeddings, graph database, or generated summaries in the required-norm path;
- no automatic expansion except transitive `requires`;
- drafts, deprecated norms, and on-demand norms excluded by default;
- stable ID ordering and bounded summaries/sections;
- local metadata parsing, with frontmatter omitted from model projections;
- explicit provenance, with external material unable to promote itself to policy;
- failure on duplicate IDs, dangling relation targets, or malformed norm files.

Future retrieval evaluation should report corpus size, candidate count, catalog bytes exposed to the
model, selected body bytes/tokens, required-rule recall, irrelevant-rule rate, abstentions, and task
outcome. A larger indexed corpus is acceptable only when the per-task selection surface remains
bounded and recall safeguards remain effective.
