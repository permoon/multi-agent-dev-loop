---
name: Multi-Agent Dev Loop
description: >
  Multi-agent collaboration loop for non-trivial implementation work —
  multi-file features or refactors, architecture decisions, schema/IAM/data
  design or changes, deploys, or any task with rollback risk or large
  blast radius. Covers both greenfield projects and existing codebases.
  Coordinates Claude (plan, review, triage, GCP deploy review,
  retrospective) + Codex (review, code) through 8 steps with fixed
  artifact paths and explicit failure routing. Skip for typos, single-line
  edits, pure exploration, or when the user requests a quick fix.
---

# Multi-Agent Dev Loop

A structured collaboration loop that coordinates Claude (planning, code review,
triage, GCP deploy review, retrospective) and Codex (plan review,
implementation). Each step produces a fixed artifact, enabling resumability,
auditability, post-deploy verification with automatic failure routing, and
retrospective evaluation for workflow improvement.

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
- Plan must be implementation-ready but not implementation-complete.
  It should give Codex enough constraints to build the right thing after
  reading the repo, without turning `plan.md` into a bundle of source files
  to paste.
- Include exact contracts, invariants, affected modules, edge cases, data
  migrations, validation expectations, and acceptance criteria.
- Use exact source artifacts only when the artifact itself is declarative or
  contract-like: SQL DDL / migration SQL, schema definitions, IAM policy,
  workflow YAML, API contracts, prompt templates, config files, or command
  examples.
- For application code, avoid full production-ready files or large copyable
  implementations. Describe behavior, interfaces, important algorithms,
  test cases, and integration points. Small snippets are OK when they clarify
  a tricky invariant or API shape, but Codex owns the final code structure.
- No pseudocode for critical logic that affects data correctness, security,
  rollback, or user-visible behavior. Express those requirements as precise
  rules, examples, truth tables, queries, contracts, or test cases rather than
  full app-code implementations.
- **Also produce `plans/<feature>/validation.md`** containing:
  - **Pre-deploy check**: environment readiness (dependent services / IAM /
    config in place)
  - **Post-deploy smoke test**: concrete steps, commands, expected output,
    quantified pass thresholds
  - **Rollback trigger**: quantified conditions (e.g., error rate > 5% for
    10 min, BQ partition missing, IAM rejection rate spike)
- Validation is produced in **two passes**:
  - **Pass 1 (now, in Step 1)**: derive from plan goals (reverse-engineered)
    and change blast radius — write the initial `validation.md`
  - **Pass 2 (later, only if Step 3.5 ran)**: revise `validation.md` with
    new smoke checks and rollback triggers covering the failure scenarios
    surfaced by Red Team — see Step 3.5 for the revision contract

#### Plan vs Implementation Boundary

The loop is useful only when the agents have distinct jobs:

- Claude owns the executable specification: intent, constraints, contracts,
  risks, validation, rollback, and the reasoning behind important choices.
- Codex owns the repository implementation: reading local patterns, choosing
  the concrete code shape, editing files, adding tests, and reporting any
  justified deviation from the plan.

`plan.md` should be strong enough that a competent engineer could implement
it consistently, but incomplete enough that Codex still has to inspect the
codebase and make implementation decisions. If a section reads like "copy
this entire file into the repo", rewrite it as contracts, behavior, examples,
and acceptance tests unless it is one of the declarative artifacts listed
above.

### Step 2: Codex reviews the plan

- `codex exec --full-auto` reviews `plan.md` + `validation.md` together
- Codex must check the plan/implementation boundary: flag any application
  source file or large copyable code block that should instead be expressed
  as contracts, behavior, examples, or tests. Declarative artifacts such as
  SQL, IAM, workflow YAML, schemas, prompts, and config are allowed when they
  are the actual deployable artifact.
- The validation plan itself must be challenged: does the smoke test actually
  verify the plan's goals? Is the rollback trigger quantified and detectable?
- Notes → `plans/<feature>/review-codex-round1.md`

### Step 3: Revise + re-review

- Adjust per `review-codex-round1.md`, send back to `codex exec --full-auto`
  for a second review
- Notes → `plans/<feature>/review-codex-round2.md` (do **not** overwrite
  round1; both rounds must remain side-by-side for audit trail)
- Max 2 round trips; if still divergent, list both views and escalate to
  the user

### Step 3.5: Red Team Test (conditional)

**Triggered for**: distributed systems, IAM changes, data destruction,
concurrency, large blast radius, or when the user requests it.

- Two teams in parallel (`run_in_background`, identical prompt):
  Claude / `codex exec --full-auto`
- **Adopt an attacker's perspective to find failure boundaries; do NOT
  propose fixes.**
- Check: hidden assumptions, dependency failures, edge inputs, misuse paths,
  rollback and blast radius — concrete failure scenarios, not abstract claims
- Aggregation: dedupe → split into "consensus (both teams) / single-team only"
  → grade by severity (must-fix / should-fix / acceptable)
- Output → `plans/<feature>/red-team.md`
- **Then revise `validation.md` (Pass 2)**: add smoke checks and rollback
  triggers covering must-fix and should-fix red-team findings. This
  revision is **required before Step 4** whenever Step 3.5 ran.
- Escalate to user before step 4

### Step 4: Codex writes code

- `codex exec --full-auto` implements per the final plan
- Codex must inspect the existing codebase and adapt to local conventions
  before editing. It should not mechanically copy app-code snippets from
  `plan.md`; snippets are constraints or examples unless explicitly labeled
  as declarative artifacts to apply verbatim.
- **Also produce `plans/<feature>/deviations.md`** listing every meaningful
  deviation from `plan.md`:
  - What `plan.md` specified vs what Codex did instead
  - Why: codebase constraint / local convention / discovered edge case /
    plan ambiguity (flag for clarification)
  - Severity: minor (cosmetic / style) or structural (behavior / contract /
    interface)
  - If no deviations, write "No deviations." as audit marker (still create
    the file)
- **Also produce smoke test script** `scripts/smoke/<feature>.sh`:
  - Implements the Post-deploy smoke test section of `validation.md`
  - Idempotent (re-runnable, no side effects)
  - exit 0 = pass; non-zero = fail, with stderr listing failed items and
    actual vs expected values
  - Verification uses sampled / read-only access; use a separate test SA
    when needed to avoid polluting prod

### Step 5: Claude reviews code

- Check code quality, security, and consistency with the plan
- Read `plans/<feature>/deviations.md` and verify each entry is justified by
  the codebase's actual structure or constraints, not by skipping required
  work. Then check the diff for silent deviations not listed there.
  Unjustified or unlisted deviations are major issues.
- Issue grading:
  - **Minor** (typos, formatting, single-line logic, comments): Claude fixes
    directly
  - **Major** (logic errors, architectural deviation, cross-file impact,
    security concerns): send review notes back to `codex exec --full-auto`
- Notes → `plans/<feature>/review-claude.md` (this is Claude's review, not
  a Codex one — kept separate from `review-codex-round{1,2}.md`)
- Report the diff after fixes

### Step 6: Pre-deploy GCP review (conditional, GCP)

**Triggered for**: high-risk GCP deploys (IAM changes, new services,
irreversible data ops, large blast radius).

- Claude reviews deploy artifacts (workflows yaml, terraform, deploy SQL,
  IAM config, Cloud Build config, etc.) while loading the relevant Google
  Cloud skills so the review reflects current GCP behavior:
  - IAM / auth surface → `google-cloud-recipe-auth`
  - BigQuery / data → `bigquery-basics`
  - Cloud Run / serverless → `cloud-run-basics`
  - GKE → `gke-basics`
  - Cloud SQL / AlloyDB → `cloud-sql-basics` / `alloydb-basics`
  - Security posture → `google-cloud-waf-security`
  - Reliability posture → `google-cloud-waf-reliability`
  - Cost posture → `google-cloud-waf-cost-optimization`
  - Networking diagnostics → `google-cloud-networking-observability`
- Focus: least-privilege IAM, region / API compatibility, recent GCP behavior
  changes, resource naming and dependency order
- Apply feedback:
  - **Default**: Claude edits (deploy artifacts are mostly yaml / SQL / shell;
    Claude already has plan context)
  - **Switch to Codex** for large changes or cross-file refactors
    (`codex exec --full-auto`)
- Notes → `plans/<feature>/review-gcp.md`
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

### Step 8: Self-Evaluation

Run once per feature, after Step 7 settles (smoke test passed, or triage and
retries concluded). Goal: capture an unbiased retrospective so SKILL.md
itself can improve over time.

**Before dispatching**: Read `rubric.md` (in this skill folder). Inline its
full content — subagent prompt framing, inputs, rubric table, score-<4
contract — into the subagent's prompt. `rubric.md` is the authoritative
source; if it conflicts with anything here, rubric wins.

- Orchestrator dispatches a fresh Claude subagent (Agent tool,
  `subagent_type: general-purpose`) with the rubric content and artifact paths
- The subagent has no prior conversation context — sees only the rubric and
  the files it is told to read. This is what makes the evaluation unbiased
  versus orchestrator self-evaluation.
- Subagent scores 5 dimensions, writes `plans/<feature>/evaluation.md`,
  and exits
- Orchestrator confirms the file exists and reports the path; does not
  re-evaluate or argue with the scores

For the roll-up cadence (every 10 evaluations or monthly), see `rubric.md`.

## Artifact Paths

```
plans/<feature>/
  plan.md                    # Step 1: implementation plan
  validation.md              # Step 1 + Step 3.5: two-pass validation plan
  red-team.md                # Step 3.5: red team output (if triggered)
  review-codex-round1.md     # Step 2: Codex plan review notes (first round)
  review-codex-round2.md     # Step 3: Codex plan review notes (second round, if needed)
  deviations.md              # Step 4: implementation deviations from plan
  review-claude.md           # Step 5: Claude code review notes
  review-gcp.md              # Step 6: GCP deploy review notes (if triggered)
  evaluation.md              # Step 8: retrospective evaluation
deploy/<feature>/            # Step 6: deploy artifacts (yaml / terraform / SQL / IAM)
scripts/smoke/<feature>.sh   # Step 4: smoke test script
runs/<timestamp>-<feature>/
  smoke.log                  # Step 7: smoke test output
  triage.md                  # Step 7: triage conclusion (if failed)
runs/rollup-<YYYYMM>.md      # Step 8: monthly / per-10-eval roll-up
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

- Before invoking Codex CLI, run `codex exec --help` first to confirm flags;
  `codex exec --full-auto` outside a git repo requires `--skip-git-repo-check`
- Subagent or external tool large output (>10KB) must be written to a repo
  file, not returned inline; messages return only file path, summary, key
  conclusion, next step
- When dispatching to Codex or a Claude subagent, the orchestrator must
  specify output format, file path, and large-output rules in the prompt
- If output is truncated or over limit, stop retrying — write to file and
  report the path

## Prerequisites

- `codex` CLI installed and authenticated (`codex exec --help` works)
- A working directory where the artifact tree can be created
- For Step 6 (GCP deploy review), the GCP skills referenced in that step
  must be installed in the Claude environment

## Examples

See `docs/examples.md` for two illustrated end-to-end runs (a new BQ table +
workflow, and a Step 7 triage). Examples are reference only — the
orchestrator does not need to read them to execute the loop.
