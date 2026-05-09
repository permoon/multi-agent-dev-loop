# multi-agent-dev-loop

一個 standalone skill，用多 agent 開發流程處理高風險實作工作。

![流程圖](./docs/demo.png)

它不是讓單一 agent 在同一段脆弱對話裡一次完成計畫、寫 code、部署和除錯，
而是把 **Claude + Codex + Gemini** 串成固定流程：

```text
計畫 -> 審查 -> 實作 -> 審查 -> 部署 -> smoke test -> triage
```

目的不是增加儀式感，而是讓自主開發在有真實爆炸半徑時，仍然**可恢復、
可檢查、比較安全**。

[English](./README.md)

## 為什麼需要它

AI coding agent 很會衝刺，但高風險工作需要的不只是速度。當任務碰到
schema、IAM、資料 pipeline、部署設定、migration 或多檔變更時，真正困難的
通常不是寫 code，而是讓計畫、假設、驗證、回滾路徑和部署後證據保持一致。

`multi-agent-dev-loop` 給 agent 一套可重複的工作模式：

- 寫 code 前先產出具體計畫
- 讓另一個 agent 挑戰計畫和驗證策略
- 實作時一併產生 smoke test
- 部署敏感變更先做額外 review
- 失敗時分流回正確步驟，而不是亂猜
- 留下 artifacts，讓人可以稽核或接手恢復

## 何時使用

適合用在非簡單實作工作：

- 多檔 feature 或 refactor
- 架構決策
- schema、IAM 或資料變更
- 部署與 migration
- 有 rollback 風險
- blast radius 大
- 需要可追蹤或可恢復的工作

不適合：

- 錯字和單行修改
- 純格式調整
- 純探索或問答
- 不會部署的一次性腳本
- 明確的 quick fix

## 它會做什麼

| 步驟 | 負責人 | 產出 |
|---|---|---|
| 1. 計畫 | Claude | `plans/<feature>/plan.md` + `validation.md` |
| 2. 計畫審查 | Codex | `plans/<feature>/review-codex.md` |
| 3. 修正 + 二審 | Claude + Codex | 修正後的計畫 artifacts |
| 3.5. Red team，條件式 | Claude + Codex + Gemini | `plans/<feature>/red-team.md` |
| 4. 實作 | Codex | 程式碼 + `scripts/smoke/<feature>.sh` |
| 5. Code review | Claude | 直接修正或退回 Codex |
| 6. 部署 review，GCP 條件式 | Gemini | `plans/<feature>/review-gemini.md` |
| 7. 驗證 + triage | Claude | `runs/<timestamp>-<feature>/{smoke.log,triage.md}` |

如果 smoke test 失敗，skill 會分類並分流：

| 失敗類型 | 分流 |
|---|---|
| 部署失敗：服務起不來、IAM 拒絕、設定錯誤 | Step 6 |
| 部署成功但行為錯 | Step 4 |
| 行為符合 code，但不符合計畫意圖 | Step 1 |
| Smoke test 誤判 | 修 `validation.md`，再從 Step 4 重跑 |

## 安裝

這個 repo 現在是 standalone skill。把整個 repo 資料夾複製到你的 agent
環境使用的 skills 目錄即可。

Codex：

```bash
mkdir -p ~/.codex/skills
cp -R /path/to/multi-agent-dev-loop ~/.codex/skills/
```

Claude Code 或其他支援 skill 的環境，請把這個資料夾複製到該工具設定的
skills 目錄。

skill 入口是：

```text
SKILL.md
```

## 前置需求

- `codex` CLI 已安裝並登入，且 `codex exec --help` 可正常執行
- `gemini` CLI 已安裝並登入，用於 red-team 與 GCP deploy review
- 一個可建立 artifact tree 的工作目錄

Gemini 只在條件式 red-team 與 GCP deploy review 需要。

## Artifact tree

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

`<feature>` 使用 kebab-case，例如 `workflow-daily-ingest`。
`<timestamp>` 使用 `YYYYMMDD-HHMMSS`。

## 輸出規範

每一步結束只回報三行：

```text
Step: <剛完成的步驟>
Artifact: <產出的檔案路徑>
Next: <下一步或卡關原因>
```

大型輸出寫進檔案，不貼在 chat。

## 範例

使用者要求：

```text
Add a daily aggregate table analytics.daily_user_summary and a workflow to
refresh it at 6am.
```

skill 會產生：

- 具體 implementation plan 與 validation plan
- Codex review notes，挑戰 schema、IAM、部署順序和 smoke 覆蓋率
- 實作與 idempotent smoke test
- Claude code review
- 如果 GCP 風險高，進行 Gemini deploy review
- smoke-test output，以及驗證失敗時的 triage

## License

[MIT](LICENSE)
