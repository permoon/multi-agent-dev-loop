---
name: Multi-Agent Dev Loop
description: >
  Multi-agent collaboration loop for non-trivial implementation work —
  multi-file features or refactors, architecture decisions, schema/IAM/data
  design or changes, deploys, or any task with rollback risk or large
  blast radius. Covers both greenfield projects and existing codebases.
  Coordinates Claude (plan, review, triage) + Codex (review, code) + Gemini
  (red team, GCP deploy review) through 7 steps with fixed artifact paths
  and explicit failure routing. Skip for typos, single-line edits, pure
  exploration, or when the user requests a quick fix.
---

# Multi-Agent Dev Loop

A structured collaboration loop that coordinates Claude (planning, code review,
triage), Codex (plan review, implementation), and Gemini (red team, GCP deploy
review). Each step produces a fixed artifact, enabling resumability,
auditability, and post-deploy verification with automatic failure routing.

## When to Trigger

Invoke this skill when ALL apply:

1. The task is **non-trivial implementation work** — multi-file features
   or refactors, architecture decisions, schema / IAM / data design or
   changes, deploy involved, or any task with rollback risk or large
   blast radius. Applies to both greenfield projects and existing codebases.
2. The task has clear scope (a feature, a refactor, a migration, an
   architectural decision), not pure exploration.
3. The user has not explicitly asked you to skip the workflow.

### Non-Trigger (skip the workflow)

- Single-line edits, typo fixes, formatting-only changes
- Pure exploration / Q&A ("how does this work?", "where is X defined?")
- One-off scripts that won't be deployed
- The user explicitly says "just do it" / "quick fix" / "no review needed"

## Workflow

### Step 1: Plan (Claude)

- Use the Plan agent → write to `plans/<feature>/plan.md`
- Plan must be concrete: actual SQL / schema / prompts / API contracts
  (no pseudocode for critical logic)
- **Also produce `plans/<feature>/validation.md`** containing:
  - **Pre-deploy check**: environment readiness (dependent services / IAM /
    config in place)
  - **Post-deploy smoke test**: concrete steps, commands, expected output,
    quantified pass thresholds
  - **Rollback trigger**: quantified conditions (e.g., error rate > 5% for
    10 min, BQ partition missing, IAM rejection rate spike)
- Validation draws from three sources: plan goals (reverse-engineered),
  change blast radius, Red Team failure scenarios (if step 3.5 ran)

### Step 2: Codex reviews the plan

- `codex exec --full-auto` reviews `plan.md` + `validation.md` together
- The validation plan itself must be challenged: does the smoke test actually
  verify the plan's goals? Is the rollback trigger quantified and detectable?
- Notes → `plans/<feature>/review-codex.md`

### Step 3: Revise + re-review

- Adjust per Codex feedback, send back to `codex exec --full-auto` for a
  second review
- Max 2 round trips; if still divergent, list both views and escalate to
  the user

### Step 3.5: Red Team Test (conditional)

**Triggered for**: distributed systems, IAM changes, data destruction,
concurrency, large blast radius, or when the user requests it.

- Three teams in parallel (`run_in_background`, identical prompt):
  Claude / `codex exec --full-auto` / `gemini -p`
- **Adopt an attacker's perspective to find failure boundaries; do NOT
  propose fixes.**
- Check: hidden assumptions, dependency failures, edge inputs, misuse paths,
  rollback and blast radius — concrete failure scenarios, not abstract claims
- Aggregation: dedupe → split into "consensus (≥2 teams) / single-team only"
  → grade by severity (must-fix / should-fix / acceptable)
- Output → `plans/<feature>/red-team.md`, escalate to user before step 4

### Step 4: Codex writes code

- `codex exec --full-auto` implements per the final plan
- **Also produce smoke test script** `scripts/smoke/<feature>.sh`:
  - Implements the Post-deploy smoke test section of `validation.md`
  - Idempotent (re-runnable, no side effects)
  - exit 0 = pass; non-zero = fail, with stderr listing failed items and
    actual vs expected values
  - Verification uses sampled / read-only access; use a separate test SA
    when needed to avoid polluting prod

### Step 5: Claude reviews code

- Check code quality, security, and consistency with the plan
- Issue grading:
  - **Minor** (typos, formatting, single-line logic, comments): Claude fixes
    directly
  - **Major** (logic errors, architectural deviation, cross-file impact,
    security concerns): send review notes back to `codex exec --full-auto`
- Report the diff after fixes

### Step 6: Pre-deploy Gemini review (conditional, GCP)

**Triggered for**: high-risk GCP deploys (IAM changes, new services,
irreversible data ops, large blast radius).

- `gemini -p` reviews deploy artifacts (workflows yaml, terraform, deploy SQL,
  IAM config, Cloud Build config, etc.)
- Focus: least-privilege IAM, region / API compatibility, recent GCP behavior
  changes, resource naming and dependency order
- Apply feedback:
  - **Default**: Claude edits (deploy artifacts are mostly yaml / SQL / shell;
    Claude already has plan context)
  - **Switch to Codex** for large changes or cross-file refactors
    (`codex exec --full-auto`)
- Notes → `plans/<feature>/review-gemini.md`
- Re-deploy after fixes

### Step 7: Post-deploy verification

Run after every deploy (regardless of whether step 6 ran).

- Run `scripts/smoke/<feature>.sh` → output to
  `runs/<timestamp>-<feature>/smoke.log`
- **Read result**:
  - exit 0 + all thresholds pass → enter monitoring window, report done
  - Otherwise → triage

**Triage** (Claude reads `smoke.log` + `plan.md` + code changes, picks the
rollback target, writes conclusion to
`runs/<timestamp>-<feature>/triage.md`):

| Failure type | Go back to |
|---|---|
| Deploy itself failed (service won't start, IAM denied) | Step 6 (fix deploy config) |
| Deploy OK but behavior wrong (logic bug) | Step 4 (fix code) |
| Behavior matches code but not plan intent | Step 1 (fix plan) |
| Smoke test false negative | Fix `validation.md`, rerun from step 4 |

- **Rollback**: if `validation.md` rollback trigger fires, rollback first,
  then triage
- **Retry cap**: step 4 ↔ 7 ≤ 3 round trips; otherwise escalate to user
- **Report**: verification summary, triage conclusion (if any), monitoring
  status

## Artifact Paths

```
plans/<feature>/
  plan.md              # Step 1: implementation plan
  validation.md        # Step 1: validation plan
  red-team.md          # Step 3.5: red team output (if triggered)
  review-codex.md      # Step 2 / 5: Codex review notes
  review-gemini.md     # Step 6: Gemini review notes (if triggered)
deploy/<feature>/      # Step 6: deploy artifacts (yaml / terraform / SQL / IAM)
scripts/smoke/<feature>.sh  # Step 4: smoke test script
runs/<timestamp>-<feature>/
  smoke.log            # Step 7: smoke test output
  triage.md            # Step 7: triage conclusion (if failed)
```

- `<feature>`: kebab-case short descriptor (e.g., `workflow-daily-ingest`)
- `<timestamp>`: `YYYYMMDD-HHMMSS`
- Commit artifacts to git for review and traceability; for `runs/`, decide
  per project (small logs OK, large logs → `.gitignore`)

## Output Contract

After each step, report exactly three lines:

1. **Step**: which step just finished
2. **Artifact**: the file path produced
3. **Next**: which step is next, or escalation reason if blocked

Brief progress, no long-form narration.

## Tool Invocation Notes

- Before invoking Gemini CLI, run `gemini --help` to confirm flags
  (headless mode blocks `write_file` by default, blocks `.tmp_*`,
  restricted to cwd)
- Same for Codex CLI; `codex exec --full-auto` outside a git repo requires
  `--skip-git-repo-check`. Run `codex exec --help` first to confirm flags
- Subagent or external tool large output (>10KB) must be written to a repo
  file, not returned inline; messages return only file path, summary, key
  conclusion, next step
- When dispatching to Codex / Gemini, the orchestrator must specify output
  format, file path, and large-output rules in the prompt
- If output is truncated or over limit, stop retrying — write to file and
  report the path

## Prerequisites

- `codex` CLI installed and authenticated (`codex exec --help` works)
- `gemini` CLI installed and authenticated (only required for steps 3.5 / 6)
- A working directory where the artifact tree can be created

## Examples

### Example 1: New BQ table + Workflow

User: "Add a new daily aggregate table `analytics.daily_user_summary` and a
workflow to refresh it at 6am."

- **Step 1** → `plans/daily-user-summary/plan.md` (table schema, partition
  strategy, source query, workflow YAML outline) + `validation.md`:
  - Pre-deploy: source tables exist, IAM SA has `roles/bigquery.jobUser`
  - Smoke test: workflow execution succeeds, today's partition has > 0 rows,
    no null in `user_id`
  - Rollback: any null in primary key → drop partition + page on-call
- **Step 2** → Codex flags: "no clustering on `user_id`, will scan full table
  on most queries"
- **Step 3** → revised plan adds clustering on `user_id`
- **Step 3.5** → skipped (low blast radius, not distributed, no IAM destruction)
- **Step 4** → Codex writes DDL, workflow YAML,
  `scripts/smoke/daily-user-summary.sh` (`bq query` + row-count assertion +
  null check)
- **Step 5** → Claude review: minor SQL style fix, applied directly
- **Step 6** → Gemini reviews workflow YAML + IAM (new service combo);
  suggests adding `connector_params.timeout` to BQ connector
- **Step 7** → deploy, run smoke test → exit 0, monitoring window started

### Example 2: Triage after smoke test failure

User: After step 7, smoke test exits 1: "expected partition row count > 0,
got 0".

- Read `runs/20260508-103000-daily-user-summary/smoke.log` → workflow
  finished with status SUCCEEDED but target partition empty
- Read `plans/daily-user-summary/plan.md` → source query filters
  `WHERE event_date = CURRENT_DATE()`
- Hypothesis: source data lands at 22:00 local (UTC+8) = next-day UTC,
  `CURRENT_DATE()` runs in UTC and looks at the wrong partition
- Triage classification: "Behavior matches code but not plan intent"
  → **Step 1** (fix plan: spec timezone explicitly)
- Write `runs/20260508-103000-daily-user-summary/triage.md`, escalate to user
  with proposed plan revision (convert to project timezone before filter, or
  add an explicit date column in the source layer)
