---
name: multi-agent-dev-loop
description: >
  Use this skill for non-trivial implementation work that needs a disciplined
  multi-agent development loop: multi-file features or refactors, architecture
  decisions, schema/IAM/data changes, deploys, migrations, rollback risk, or
  large blast radius. Coordinates Claude for planning/review/triage, Codex for
  plan review and implementation, and Gemini for red-team or GCP deploy review.
  Produces fixed artifacts for plan, validation, code review, smoke tests,
  deployment checks, and failure routing. Skip for typos, single-line edits,
  pure exploration, one-off scripts, or when the user asks for a quick fix.
---

# Multi-Agent Dev Loop

Use this skill to turn high-risk autonomous coding into an auditable loop:
plan, challenge, implement, review, deploy, verify, and route failures back to
the right step.

The loop coordinates:

- Claude: planning, code review, triage
- Codex: plan review, implementation
- Gemini: red team, GCP deploy review

Each step writes a fixed artifact so the work is resumable, reviewable, and
safe to hand between agents.

## Trigger Rules

Use this skill when all are true:

1. The task is non-trivial implementation work: multi-file feature/refactor,
   architecture decision, schema/IAM/data change, deploy, migration, rollback
   risk, or large blast radius.
2. The task has a clear scope: a feature, refactor, migration, deploy, or
   architectural decision.
3. The user has not explicitly asked to skip the workflow.

Skip this skill for:

- Single-line edits, typo fixes, formatting-only changes
- Pure exploration or Q&A
- One-off scripts that will not be deployed
- Requests phrased as "quick fix", "just do it", or "no review needed"

## Workflow

### Step 1: Plan

Write:

- `plans/<feature>/plan.md`
- `plans/<feature>/validation.md`

The plan must be concrete. Include actual SQL, schemas, prompts, APIs, file
paths, rollout steps, and contracts where relevant. Avoid pseudocode for
critical logic.

The validation plan must include:

- Pre-deploy checks: services, IAM, config, datasets, secrets, and dependencies
- Post-deploy smoke test: commands, expected output, and quantified thresholds
- Rollback trigger: quantified, observable conditions

Validation should be derived from the plan goals, the blast radius, and any red
team findings.

### Step 2: Codex Plan Review

Ask Codex to review `plan.md` and `validation.md` together.

Require Codex to challenge:

- Whether the plan can actually meet the goal
- Whether the smoke test proves the goal
- Whether rollback triggers are quantified and detectable
- Whether hidden dependencies, permissions, or data assumptions are missing

Write notes to:

- `plans/<feature>/review-codex.md`

### Step 3: Revise And Re-Review

Revise the plan from Codex feedback. Send it back for one more Codex review.

Limit this to 2 review round trips. If disagreement remains, summarize both
positions and escalate to the user.

### Step 3.5: Red Team Test

Run this step for distributed systems, IAM changes, destructive data changes,
concurrency, large blast radius, or explicit user request.

Run three independent red-team passes when available:

- Claude
- `codex exec --full-auto`
- `gemini -p`

Prompt each reviewer to adopt an attacker's perspective, find failure
boundaries, and avoid proposing fixes. Ask for concrete failure scenarios:
hidden assumptions, dependency failures, edge inputs, misuse paths, rollback
holes, and blast-radius surprises.

Aggregate results into:

- consensus issues: found by at least 2 reviewers
- single-team issues
- severity: must-fix, should-fix, acceptable

Write:

- `plans/<feature>/red-team.md`

Escalate must-fix findings to the user before implementation.

### Step 4: Implement

Ask Codex to implement the final reviewed plan.

Also produce:

- `scripts/smoke/<feature>.sh`

The smoke script must:

- Implement the post-deploy smoke test from `validation.md`
- Be idempotent and safe to rerun
- Use read-only or sampled verification where possible
- Exit `0` on pass
- Exit non-zero on fail, writing failed checks and actual-vs-expected values to
  stderr

Use a separate test service account when needed to avoid polluting production.

### Step 5: Code Review

Claude reviews the implementation for:

- Consistency with `plan.md`
- Correctness of the smoke test
- Security and permission boundaries
- Rollback and migration safety
- Style and consistency with the existing codebase

Fix minor issues directly: typos, comments, formatting, single-line logic.

Send major issues back to Codex: architecture drift, logic errors, cross-file
impact, security concerns, or non-trivial test changes.

Report the diff after fixes.

### Step 6: Pre-Deploy Gemini Review

Run this for high-risk GCP deploys: IAM changes, new services, irreversible data
operations, or large blast radius.

Ask Gemini to review deploy artifacts such as:

- Workflow YAML
- Terraform
- Deploy SQL
- IAM config
- Cloud Build config
- Scheduler/Eventarc/Pub/Sub config

Focus the review on least privilege, region/API compatibility, recent GCP
behavior, naming, dependency order, and rollback safety.

Write:

- `plans/<feature>/review-gemini.md`

Claude may apply small YAML/SQL/shell fixes directly. Send large cross-file
changes back to Codex.

### Step 7: Post-Deploy Verification And Triage

After every deploy, run:

- `scripts/smoke/<feature>.sh`

Write output to:

- `runs/<timestamp>-<feature>/smoke.log`

If the smoke test passes, report verification summary and monitoring status.

If it fails, read `smoke.log`, `plan.md`, `validation.md`, and the code diff.
Classify the failure and route it:

| Failure type | Go back to |
|---|---|
| Deploy failed: service will not start, IAM denied, config invalid | Step 6 |
| Deploy succeeded but behavior is wrong | Step 4 |
| Behavior matches code but not plan intent | Step 1 |
| Smoke test is a false negative | Fix `validation.md`, then rerun from Step 4 |

If the rollback trigger in `validation.md` fires, rollback first, then triage.

Limit Step 4 to Step 7 retries to 3 round trips. Escalate after that.

Write triage conclusions to:

- `runs/<timestamp>-<feature>/triage.md`

## Artifact Paths

Use kebab-case for `<feature>`, such as `workflow-daily-ingest`.
Use `YYYYMMDD-HHMMSS` for `<timestamp>`.

```text
plans/<feature>/
  plan.md
  validation.md
  red-team.md
  review-codex.md
  review-gemini.md
deploy/<feature>/
scripts/smoke/<feature>.sh
runs/<timestamp>-<feature>/
  smoke.log
  triage.md
```

Commit planning, review, deploy, and smoke test artifacts when they are useful
for traceability. Decide per project whether `runs/` logs belong in git.

## Output Contract

After each step, report exactly three lines:

```text
Step: <step just finished>
Artifact: <file path produced>
Next: <next step or escalation reason>
```

Keep progress notes short. Put large outputs in files, not chat.

## Tool Notes

Before first use in a session, check:

- `codex exec --help`
- `gemini --help`

Use `codex exec --full-auto` for Codex review and implementation. If outside a
git repo, confirm whether `--skip-git-repo-check` is required.

Before invoking Gemini, confirm the available flags. Gemini headless modes and
filesystem restrictions may differ by version.

When dispatching work to Codex or Gemini, always specify:

- The exact task
- Input files to read
- Output file path to write
- That large output must go to a file
- The expected summary format

If output is truncated or too large, stop retrying inline and write it to a
file.

## Prerequisites

- `codex` CLI installed and authenticated
- `gemini` CLI installed and authenticated for red-team and GCP deploy review
- A working directory where artifact paths can be created

## Examples

### New BigQuery Table And Workflow

User asks:

```text
Add a daily aggregate table analytics.daily_user_summary and a workflow to
refresh it at 6am.
```

Expected loop:

- Step 1 writes a table schema, partition strategy, source query, workflow
  outline, validation plan, row-count smoke test, null-key check, and rollback
  trigger.
- Step 2 Codex challenges clustering, partition filters, IAM, and smoke-test
  coverage.
- Step 3 revises the plan.
- Step 4 Codex writes DDL, workflow YAML, and a smoke script.
- Step 5 Claude reviews SQL/YAML and smoke behavior.
- Step 6 Gemini reviews GCP deployment if new IAM/services are involved.
- Step 7 smoke test verifies workflow success and target partition health.

### Triage After Smoke Test Failure

Smoke test fails:

```text
expected partition row count > 0, got 0
```

Triage:

- Read `smoke.log`: workflow succeeded but target partition is empty.
- Read `plan.md`: source query filters `WHERE event_date = CURRENT_DATE()`.
- Infer likely timezone mismatch if data lands on local-day boundaries.
- Classify as "behavior matches code but not plan intent".
- Route back to Step 1 to fix the plan with explicit timezone semantics.
- Write conclusion to `runs/<timestamp>-<feature>/triage.md`.
