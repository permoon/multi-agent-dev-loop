# Evaluation Rubric

> Authoritative source for **Step 8 (Self-Evaluation)** of the Multi-Agent
> Dev Loop. `SKILL.md` references this file. If `SKILL.md` and this file
> conflict, this file wins.

## Subagent Prompt Framing

> You are an independent workflow evaluator. You did not write the plan,
> review, or code. Score strictly per the rubric. For any score below 4,
> cite `file:line` or artifact section as evidence, state impact, and
> propose a concrete SKILL.md revision. Write to
> `plans/<feature>/evaluation.md` and exit.

## Inputs the Subagent Must Read

- **Required**: `plan.md`, `validation.md`, `review-codex-round1.md`,
  `review-codex-round2.md` (if Step 3 ran a second round), `deviations.md`,
  `review-claude.md`, `scripts/smoke/<feature>.sh`,
  `runs/<timestamp>-<feature>/smoke.log`, git diff for the feature's
  commit range
- **Conditional**: `red-team.md` (if Step 3.5 ran), `review-gcp.md` (if
  Step 6 ran), `runs/<timestamp>-<feature>/triage.md` (if Step 7 triaged)

## Rubric (1–5 with anchors)

| # | Dimension | 1 | 3 | 5 |
|---|---|---|---|---|
| 1 | Plan Quality | `plan.md` contains large app-code blocks, or `validation.md` missing a section | Structure complete but rollback trigger not quantified | Fully respects Plan vs Implementation Boundary; all `validation.md` sections quantified |
| 2 | Review Usefulness | Reviews missed issues that surfaced in Step 7 | Reviews caught some issues but added noise / false positives | Reviews caught the issues that mattered, minimal noise |
| 3 | Implementation Drift | `deviations.md` missed silent deviations (verifiable from diff) | Deviations recorded but rationale weak | Deviations completely recorded with codebase-grounded rationale |
| 4 | Trigger Correctness | In hindsight a quick fix — full loop was overkill | Loop justified but some steps added little value | Blast radius genuinely required the full loop |
| 5 | Time Efficiency | record-only: wall-clock, Codex / subagent call counts (no anchor) |||

## For each score < 4

Provide:

- **Evidence**: `file:line` or artifact section
- **Impact**: time, bug, rollback
- **Suggested SKILL.md revision**: concrete diff target

## Roll-up

Cadence: every 10 evaluations or monthly, whichever first.

- Orchestrator dispatches a second subagent to aggregate
  `plans/*/evaluation.md` since the last roll-up
- Output → `runs/rollup-<YYYYMM>.md` with per-dimension average / minimum,
  recurring sub-4 dimensions, and repeated SKILL.md revision suggestions
- Propose SKILL.md changes when the same suggestion appears ≥ 2 times
