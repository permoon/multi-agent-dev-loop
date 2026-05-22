# Examples

Two illustrated runs of the Multi-Agent Dev Loop. **Reference only** — the
orchestrator does not need to read this file to execute the skill.

## Example 1: New BQ table + Workflow

User: "Add a new daily aggregate table `4D_datamart.dm_kol_daily` and a
workflow to refresh it at 6am."

- **Step 1** → `plans/dm-kol-daily/plan.md` (table DDL/schema, partition
  strategy, source query, workflow YAML as a declarative artifact) +
  `validation.md`:
  - Pre-deploy: source tables exist, IAM SA has `roles/bigquery.jobUser`
  - Smoke test: workflow execution succeeds, today's partition has > 0 rows,
    no null in `kol_id`
  - Rollback: any null in primary key → drop partition + page on-call
- **Step 2** → Codex flags: "no clustering on `kol_id`, will scan full table
  on most queries"
- **Step 3** → revised plan adds clustering on `kol_id`
- **Step 3.5** → skipped (low blast radius, not distributed, no IAM destruction)
- **Step 4** → Codex applies the DDL and workflow YAML from `plan.md` into
  deploy artifacts, adapts them to repo layout if needed, and writes
  `scripts/smoke/dm-kol-daily.sh` (`bq query` + row-count assertion +
  null check)
- **Step 5** → Claude review: minor SQL style fix, applied directly
- **Step 6** → Claude reviews workflow YAML + IAM (new service combo) with
  `bigquery-basics` + `google-cloud-recipe-auth` +
  `google-cloud-waf-reliability` loaded; suggests adding
  `connector_params.timeout` to BQ connector
- **Step 7** → deploy, run smoke test → exit 0, monitoring window started
- **Step 8** → subagent reads all artifacts; scores Plan 5 / Reviews 4 /
  Drift 5 / Trigger 5; writes `plans/dm-kol-daily/evaluation.md`

## Example 2: Triage after smoke test failure

User: After step 7, smoke test exits 1: "expected partition row count > 0,
got 0".

- Read `runs/20260508-103000-dm-kol-daily/smoke.log` → workflow finished
  with status SUCCEEDED but target partition empty
- Read `plans/dm-kol-daily/plan.md` → source query filters
  `WHERE event_date = CURRENT_DATE()`
- Hypothesis: source data lands at 22:00 local (UTC+8) = next-day UTC,
  `CURRENT_DATE()` runs in UTC and looks at the wrong partition
- Triage classification: "Behavior matches code but not plan intent"
  → **Step 1** (fix plan: spec timezone explicitly)
- Write `runs/20260508-103000-dm-kol-daily/triage.md`, escalate to user
  with proposed plan revision (add `event_date_tw` column or convert to
  Asia/Taipei before filter)
