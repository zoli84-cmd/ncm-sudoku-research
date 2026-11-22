# Review plan: Prompt audit of the Claude Code configuration (2026-11-22)
Artifact: .reviews/prompt-audit/round-final/artifact.md (version 2; version 1 in round-1/)
Tier: medium — no high trigger; the proposed edits span four project instruction files and three user-level files under `~/.claude` and `~/AGENTS.md`, which are outside git and not undone by `git revert`   (overridden by user: no)

| Step | Reviewers | Scope | Status | Accepted blocker/major |
|---|---|---|---|---|
| R1 | sol,carbon | full | done 2026-11-22 (triage approved by the user; fixes applied in version 2) | 3 (CARBON-1, CARBON-2 + SOL-3, CARBON-3 + SOL-2) + 1 partial (SOL-1 + CARBON-6) |
| Final | astra | changed sections | done 2026-11-22 (triage approved; hunks applied) | 2 (ASTRA-1, ASTRA-2) |
