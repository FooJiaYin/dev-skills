# code-review：評分 agent 中斷要重派

```
現在❌                                        改後✓
Phase 3 scorer 被中斷／結果沒送回             Phase 3 scorer 被中斷／結果沒送回
        │                                             │
        ▼                                             ▼
orchestrator 自己補分數                        重派同一個 scorer
（使用者打斷：「use agents」）                 orchestrator 永不自己評分
```

# Description

- sparktoy-erp 的 B5 wrap-up 跑 `/code-review` 時，Phase 3 有兩個 Haiku scorer 被中斷、三個的回報沒送到 orchestrator。orchestrator 改成自己量測、自己評分，使用者中途糾正「use agents」。

# Changes Made

- `skills/code-review/SKILL.md` Phase 3：加一句「scorer 中斷或結果沒到就重派；orchestrator 不自己評分」。

# Result

- 重派後五個 scorer 都在同一輪回報（85／70／70／55／0），REVIEW 檔正常產出。規則只補一句，不改流程。
