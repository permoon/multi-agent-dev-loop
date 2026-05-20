# multi-agent-dev-loop

A standalone skill for running high-risk implementation work through a
multi-agent development loop.

![Workflow diagram](./docs/demo.png)

Instead of asking one agent to plan, code, deploy, and debug in a single fragile
thread, this skill coordinates **Claude + Codex + Gemini** through a fixed
workflow:

```text
plan -> review -> code -> review -> deploy -> smoke test -> triage -> retrospective
```

The goal is not ceremony. The goal is to make autonomous development
**resumable, inspectable, and safer when the blast radius is real**.

[繁體中文](./README.zh-TW.md)

## Why this exists

AI coding agents are good at moving fast, but risky work needs more than speed.
When a task touches schema, IAM, data pipelines, deploy config, migrations, or
multiple files, the hard part is usually not writing code. It is keeping the
plan, assumptions, validation, rollback path, and post-deploy evidence aligned.

`multi-agent-dev-loop` gives the agent a repeatable operating model:

- Write a concrete plan before coding
- Challenge the plan and validation strategy with another agent
- Produce a smoke test as part of implementation
- Review deploy-sensitive changes before release
- Route failures back to the correct step instead of guessing
- Run an unbiased retrospective so the workflow keeps improving
- Leave artifacts behind so humans can audit or resume the work

## When to use it

Use this skill for non-trivial implementation work:

- Multi-file features or refactors
- Architecture decisions
- Schema, IAM, or data changes
- Deploys and migrations
- Rollback risk
- Large blast radius
- Work that should be auditable or resumable

Skip it for:

- Typos and single-line edits
- Formatting-only changes
- Pure exploration or Q&A
- One-off scripts that will not be deployed
- Explicit quick fixes

## What it does

| Step | Owner | Output |
|---|---|---|
| 1. Plan | Claude | `plans/<feature>/plan.md` + `validation.md` (Pass 1) |
| 2. Plan review (round 1) | Codex | `plans/<feature>/review-codex-round1.md` |
| 3. Revise + re-review (round 2) | Claude + Codex | `plans/<feature>/review-codex-round2.md` |
| 3.5. Red team, conditional | Claude + Codex + Gemini | `plans/<feature>/red-team.md` + revised `validation.md` (Pass 2) |
| 4. Implement | Codex | source files + `plans/<feature>/deviations.md` + `scripts/smoke/<feature>.sh` |
| 5. Code review | Claude | `plans/<feature>/review-claude.md` (inline fixes or notes back to Codex) |
| 6. Deploy review, conditional GCP | Gemini | `plans/<feature>/review-gemini.md` |
| 7. Verify + triage | Claude | `runs/<timestamp>-<feature>/{smoke.log,triage.md}` |
| 8. Self-evaluation | Claude subagent | `plans/<feature>/evaluation.md` (+ periodic `runs/rollup-<YYYYMM>.md`) |

If the smoke test fails, the skill classifies the failure and routes it:

| Failure type | Route |
|---|---|
| Deploy failed: service will not start, IAM denied, invalid config | Step 6 |
| Deploy succeeded but behavior is wrong | Step 4 |
| Behavior matches code but not the intended plan | Step 1 |
| Smoke test is a false negative | Fix `validation.md`, then rerun from Step 4 |

## Install

This repository is now a standalone skill. Copy the repository folder into the
skills directory used by your agent environment.

For Codex:

```bash
mkdir -p ~/.codex/skills
cp -R /path/to/multi-agent-dev-loop ~/.codex/skills/
```

For Claude Code or other skill-compatible environments, copy this folder into
that tool's configured skills directory.

The skill entrypoint is:

```text
SKILL.md
```

## Prerequisites

- `codex` CLI installed and authenticated (`codex exec --help` works)
- `gemini` CLI installed and authenticated for red-team and GCP deploy review
- A working directory where the artifact tree can be created

Gemini is only needed for conditional red-team and GCP deploy-review steps.

## Artifact tree

```text
plans/<feature>/
  plan.md
  validation.md
  red-team.md
  review-codex-round1.md
  review-codex-round2.md
  deviations.md
  review-claude.md
  review-gemini.md
  evaluation.md
deploy/<feature>/
scripts/smoke/<feature>.sh
runs/<timestamp>-<feature>/
  smoke.log
  triage.md
runs/rollup-<YYYYMM>.md
```

`<feature>` should be kebab-case, such as `workflow-daily-ingest`.
`<timestamp>` uses `YYYYMMDD-HHMMSS`.

## Output contract

After each step, the skill reports exactly three lines:

```text
Step: <step just finished>
Artifact: <file path produced>
Next: <next step or escalation reason>
```

Large outputs go into files, not chat.

## Example

User request:

```text
Add a daily aggregate table analytics.daily_user_summary and a workflow to
refresh it at 6am.
```

The skill produces:

- A concrete implementation plan and a two-pass validation plan
- Codex review notes across two rounds, challenging schema, IAM, deploy order, and smoke coverage
- Implementation plus a `deviations.md` audit log and an idempotent smoke test
- Claude code review notes (`review-claude.md`)
- Optional Gemini deploy review if GCP risk is high
- Smoke-test output and triage if verification fails
- An unbiased retrospective (`evaluation.md`) scoring plan quality, review usefulness, implementation drift, and trigger correctness

## License

[MIT](LICENSE)
