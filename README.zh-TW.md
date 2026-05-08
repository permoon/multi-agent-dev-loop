# multi-agent-dev-loop

Claude Code plugin,將 **Claude + Codex + Gemini** 串成一條 7 步工作流,專處理非小型的實作任務 — 多檔功能、重構、schema/IAM/資料變更、部署,或任何有 rollback 風險、blast radius 較大的工作。

每一步產出固定的 artifact,具備**可恢復性**、**可稽核**、**部署後自動驗證**,失敗時自動路由回正確的上游步驟修補。

## 流程概覽

| 步驟 | 負責人 | 產出 |
|---|---|---|
| 1. 計畫 | Claude | `plans/<feature>/plan.md` + `validation.md` |
| 2. 計畫審查 | Codex | `plans/<feature>/review-codex.md` |
| 3. 修正 + 二審 | Claude + Codex | 修正後的 `plan.md` |
| 3.5. Red Team(條件式) | Claude + Codex + Gemini | `plans/<feature>/red-team.md` |
| 4. 寫 code | Codex | 程式碼 + `scripts/smoke/<feature>.sh` |
| 5. Code 審查 | Claude | 直接修正或退回 Codex |
| 6. 部署前審(GCP,條件式) | Gemini | `plans/<feature>/review-gemini.md` |
| 7. 部署後驗證 | Claude | `runs/<timestamp>-<feature>/{smoke.log,triage.md}` |

Step 7 smoke test 失敗時,triage 會把失敗類型對應回正確的步驟(部署問題 → Step 6、邏輯錯 → Step 4、計畫沒對齊 → Step 1、smoke 誤判 → 修 `validation.md`)。

## 何時觸發

任務符合以下任一即觸發:多檔功能或重構、架構決策、schema/IAM/資料變更、有部署、有 rollback 風險、blast radius 大。

**跳過**:錯字、單行編輯、純探索、quick fix。

## 安裝

```
/plugin marketplace add permoon/multi-agent-dev-loop
/plugin install multi-agent-dev-loop
```

## 前置需求

- [`codex`](https://github.com/openai/codex) CLI 已安裝並登入(`codex exec --help` 可正常執行)
- [`gemini`](https://github.com/google-gemini/gemini-cli) CLI 已安裝並登入(僅 Step 3.5 / 6 需要)
- 一個可建立 artifact 樹(`plans/`, `deploy/`, `scripts/smoke/`, `runs/`)的工作目錄

## Artifact 樹

```
plans/<feature>/
  plan.md              # Step 1:實作計畫
  validation.md        # Step 1:部署前/smoke/rollback 條件
  red-team.md          # Step 3.5(若觸發)
  review-codex.md      # Step 2 / 5
  review-gemini.md     # Step 6(若觸發)
deploy/<feature>/      # Step 6:部署 artifact
scripts/smoke/<feature>.sh   # Step 4:smoke 測試腳本
runs/<timestamp>-<feature>/
  smoke.log            # Step 7
  triage.md            # Step 7(若失敗)
```

## 輸出規範

每一步結束只回報三行:

1. **Step**:剛完成的步驟
2. **Artifact**:產出的檔案路徑
3. **Next**:下一步或卡關原因

精簡進度,無冗長敘述。

## License

[MIT](LICENSE)
