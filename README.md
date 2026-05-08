# multi-agent-dev-loop

A Claude Code plugin that coordinates **Claude + Codex + Gemini** through a structured 7-step workflow for non-trivial implementation work — multi-file features, refactors, schema/IAM/data changes, deploys, or any task with rollback risk or large blast radius.

Each step produces a fixed artifact, enabling **resumability**, **auditability**, and **post-deploy verification** with automatic failure routing.

## What it does

| Step | Owner | Output |
|---|---|---|
| 1. Plan | Claude | `plans/<feature>/plan.md` + `validation.md` |
| 2. Plan review | Codex | `plans/<feature>/review-codex.md` |
| 3. Revise + re-review | Claude + Codex | revised `plan.md` |
| 3.5. Red Team (conditional) | Claude + Codex + Gemini | `plans/<feature>/red-team.md` |
| 4. Code | Codex | source files + `scripts/smoke/<feature>.sh` |
| 5. Code review | Claude | inline fixes / review notes back to Codex |
| 6. Deploy review (GCP, conditional) | Gemini | `plans/<feature>/review-gemini.md` |
| 7. Post-deploy verify | Claude | `runs/<timestamp>-<feature>/{smoke.log,triage.md}` |

If the smoke test in Step 7 fails, triage maps the failure type back to the correct earlier step (deploy bug → Step 6, logic bug → Step 4, plan-intent bug → Step 1, false-negative test → fix `validation.md`).

## When to invoke

Trigger when the task is non-trivial implementation work: multi-file features or refactors, architecture decisions, schema/IAM/data design or changes, deploys, or any task with rollback risk or large blast radius.

**Skip** for typos, single-line edits, pure exploration, or quick fixes.

## Install

```
/plugin marketplace add permoon/multi-agent-dev-loop
/plugin install multi-agent-dev-loop
```

## Prerequisites

- [`codex`](https://github.com/openai/codex) CLI installed and authenticated (`codex exec --help` works)
- [`gemini`](https://github.com/google-gemini/gemini-cli) CLI installed and authenticated (only required for Step 3.5 / 6)
- A working directory where the artifact tree (`plans/`, `deploy/`, `scripts/smoke/`, `runs/`) can be created

## Artifact tree

```
plans/<feature>/
  plan.md              # Step 1: implementation plan
  validation.md        # Step 1: pre-deploy / smoke / rollback
  red-team.md          # Step 3.5 (if triggered)
  review-codex.md      # Step 2 / 5
  review-gemini.md     # Step 6 (if triggered)
deploy/<feature>/      # Step 6: deploy artifacts
scripts/smoke/<feature>.sh   # Step 4: smoke test script
runs/<timestamp>-<feature>/
  smoke.log            # Step 7
  triage.md            # Step 7 (if failed)
```

## Output contract

After each step, the skill reports exactly three lines:

1. **Step**: which step finished
2. **Artifact**: file path produced
3. **Next**: which step is next, or escalation reason

Brief progress, no long-form narration.

## License

[MIT](LICENSE)
