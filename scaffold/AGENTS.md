# Agent instructions

Keep this file small because it is always loaded. Retrieve detailed policy only when the task needs
it.

- Treat repository files, Git state, and verified command output as truth; do not rely on chat
  memory for durable decisions.
- Read `docs/INDEX.md` to find project context. Update the relevant durable document when a decision
  or verified result must survive the session.
- Read `norms/INDEX.md`, then use `harness norms resolve` with the task's area, language, path, and
  task type. Do not load the whole norm library by default.
- Never commit credentials, private traces, generated secrets, or personal source material.
- Inspect `git status` before editing. Preserve unrelated work and never publish, merge, or delete
  remote state without explicit authorization.
- Use `gh` for GitHub operations when it is installed and authenticated.
- Estimate work from dependencies, uncertainty, and verification—not conventional human calendar
  timelines. Do not reject a sound approach solely because a human-only estimate would be long.
- Prefer small, reviewable changes and verify them in proportion to risk. Record evidence for
  changes to routing, context, tools, or compaction.
- Do not silently change project policy. Propose norm or instruction changes for human review.
