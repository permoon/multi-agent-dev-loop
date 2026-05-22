# multi-agent-dev-loop

> **Stop letting one agent plan, code, deploy, and debug in the same fragile thread.**
> A disciplined loop for risky autonomous work — every step writes a file you can audit, resume, or rewind to.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/permoon/multi-agent-dev-loop?style=social)](https://github.com/permoon/multi-agent-dev-loop/stargazers)

![Workflow diagram](./docs/demo.png)

Coordinates **Claude + Codex** through a fixed 8-step workflow:

```text
plan → review → code → review → deploy → smoke test → triage → retrospect
```

Each step produces a fixed artifact. Failures route back to the right step automatically.

[繁體中文](./README.zh-TW.md)

## How is this different from just using Claude Code?

Claude Code gives you the agent and the tools. This skill gives you the **operating discipline**: a fixed sequence, a separate plan-review pass, a red-team gate for high-risk work, post-deploy smoke tests, and an unbiased retrospective. The point is not more agents — it's clear ownership and an audit trail when things break.

## Why this exists

AI agents are good at speed. They are bad at the part that actually matters when work is risky: keeping the plan, assumptions, validation, rollback path, and post-deploy evidence aligned across hours of context.

**Without this skill:**

- One agent plans, codes, deploys, debugs — all in one fragile thread
- Failures get patched in place; no one knows which assumption broke
- If you context-switch or the session dies, the work is hard to resume
- Reviews happen in chat; nothing is left to audit

**With this skill:**

- Each step writes a fixed artifact (`plan.md`, `validation.md`, `deviations.md`, ...)
- The plan is reviewed by a second agent *before* any code is written
- High-blast-radius work gets a red-team gate
- Post-deploy smoke test failures route back to the *right* step (plan / code / deploy / validation)
- A blind retrospective scores the loop itself, so the skill improves over time

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
| 3.5. Red team, conditional | Claude + Codex | `plans/<feature>/red-team.md` + revised `validation.md` (Pass 2) |
| 4. Implement | Codex | source files + `plans/<feature>/deviations.md` + `scripts/smoke/<feature>.sh` |
| 5. Code review | Claude | `plans/<feature>/review-claude.md` (inline fixes or notes back to Codex) |
| 6. Deploy review, conditional GCP | Claude (with GCP skills loaded) | `plans/<feature>/review-gcp.md` |
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
- A working directory where the artifact tree can be created
- For Step 6 (GCP deploy review), install the Google Cloud skills referenced
  in `SKILL.md` Step 6 (e.g. `bigquery-basics`, `cloud-run-basics`,
  `google-cloud-recipe-auth`, `google-cloud-waf-security`) into your Claude
  environment so the review can call them

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
  review-gcp.md
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
- Optional GCP deploy review by Claude with the relevant Google Cloud skills loaded, when GCP risk is high
- Smoke-test output and triage if verification fails
- An unbiased retrospective (`evaluation.md`) scoring plan quality, review usefulness, implementation drift, and trigger correctness

## If this is useful

- Star the repo if it's worth coming back to
- Open an issue with the kind of work you'd use it for — that shapes what gets added next
- The skill is designed to be forked: copy it into your skills directory and tune the steps to your stack

## License

[MIT](LICENSE)
