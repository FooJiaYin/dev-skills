# 開 subagent、開 session、跨 session 協作

派 subagent、開新 session、或跟其他 session 協作之前先讀這份。防睡、背景等待結束就接著做、收到 peer 訊息不代表任務結束這三條同時留在 `~/.claude/CLAUDE.md`（隨時都要遵守）。

## 派 agent 之前

- 防睡由 hook（`dev-skills/bin/keep-awake.py`）處理：派 agent 時自動 caffeinate 2 小時，Remote Control 時撐到 session 結束。**不要自己開或 kill caffeinate，絕不 `pkill`／`killall caffeinate`**（會殺掉使用者和其他 session 的）。
- **Fan-out 前 `ls` 確認每個共用輸入（指示檔、資料檔）都在**；共用指示檔不要放在會被重建腳本清空的資料夾（seen：重建腳本 `rm *.md` 連指示檔一起刪，17 個 agent 空跑）。
- **要 agent 產出長檔時，prompt 一律寫明「分段寫入：先 Write 前段，之後每段用 Edit 追加；每欄精簡在一行」**。一次 Write 整份長輸出會 API 逾時，或 20–40 分鐘無動靜看似卡死。判斷卡住要看輸入規模與同批其他 agent 的耗時，不要只看時間（seen：誤判卡住而重派，原 agent 隨後正常交件）。
- **Subagent 模型：不要用 Fable。** 抽取、分類、歸納用 `sonnet`；需要判斷與綜合的撰寫用 `opus`。先派 1–2 個試跑確認品質再全量派出。
- **Fan-out prompt 寫明「不要再派 agent，自己依序做完」。** 子 agent 回報「未完成」時，先用 `ListAgents` 看它派出的子 agent 是否還在跑，再決定接續或重派（seen：兩組交回未完成，其子 agent 其實還在跑，叫它重做差點雙寫同一批檔）。回報進度一律 `ls` 輸出檔來數，不憑記憶。
- **WebSearch 整個 session（主對話＋所有子 agent）共用 200 次，文件未記載、無設定可調；WebFetch 不受限。** 研究型 fan-out 前先估「系統數 × 約 20 次」，超過就分到不同 session 跑，或在 prompt 直接給文件網址讓 agent 用 WebFetch。
- **派實作 agent 前，把任務 `# Context`／會議裡每一條具體的 UI 要求（放哪裡、長怎樣、用語）逐字抄進 prompt 當驗收條件；交回時逐條核對（用 `/align end`），沒做到的直接告訴我。** 只寫邏輯不寫位置，agent 會放在它覺得方便的地方。（Seen：會議寫「參數介面將類似現有稅費係數欄位」，prompt 只寫換算規則，利潤率被塞進每個公式的「編輯」步驟表，我問「為什麼沒看到利潤input？在哪裡」才發現。）
- **agent 要寫呼叫外部 CLI 的程式時，brief 裡貼上已驗證的指令與 `--help` 片段**；沒驗證過的旗標組合在整合時實跑一次，不要讓 agent 猜。（Seen：quick-review 的 `run.py` 假設 `codex exec review --uncommitted` 可帶 prompt，實跑才發現不行。）
- **brief 一律要求邊做邊落地**：每完成一步就寫出來——程式碼每個修正各自 commit、結果逐步附加到 repo 裡的檔案（不是最後一次寫整份），並維護一份進度檔（做完哪一步、下一步是什麼），讓 session 重啟後接得回來。（Seen：一個 session 重啟四次，瀏覽器測試、review 修正、角色驗證的 agent 都被殺，前三次產物只在 scratchpad 或還沒寫出，全部重跑；改成逐步 commit＋進度檔後才接得回來。）

## agent 執行中與交件

- **使用者中斷（Esc）與 `/compact` 會停掉所有背景 agent**，被停的不能 SendMessage 接續、也不能自行重派（要使用者明說）。中斷或 compact 之後，先核對預期的輸出檔是否存在、`tasks/<id>.output` 的 mtime 是否還在動，不要空等通知。要重派時，先用腳本從 `tasks/<id>.output`（JSONL）抽出 `thinking` 區塊的尾段約 2 萬字存成草稿，連同原始輸入給新 agent 接續——不要自己讀那個檔（會爆 context）。API 逾時失敗的 agent 則先試 SendMessage 接續，不要直接重派。
- **背景等待（deploy、build、CI）一結束就接著做下一步並回報，不要停下來等我提醒。** 同時輪詢多件事時，別讓慢的（GHCR build）擋住快的（Vercel 已 READY）該做的驗證；已核可的下一步直接做。（Seen：Vercel 正式部署早就好了，卻等到我打「ready」才驗證，被說「you should not wait for me to remind you it's complete」。）
- **agent 的暫存產物（截圖、量測用的臨時頁面、草稿）一律寫在 scratchpad，不准寫進 repo 工作目錄**；brief 裡寫明輸出路徑。交件後 `git status` 檢查有沒有冒出不明檔案。（Seen：截圖被寫進 `web/v1/qa/`、效能比對頁 `_perf-before.html` 放在網站資料夾，另一個 session 打包部署時差點一起帶上去。）使用者要的交付檔（xlsx、匯出檔、範例檔）不是暫存產物，不放 scratchpad：放在使用者找得到、跟用途相符的位置（例如專案旁的資料夾、對應文件的 artifacts 資料夾或 `~/Downloads`），給絕對路徑；scratchpad 只放產生它的中間腳本。（Seen：WACA 範例 xlsx 放 scratchpad，被說「output should not save in scratchpad」。）**session 重啟會清空 scratchpad**：會反覆重跑的產生腳本（報告頁、截圖腳本）一開始就放對地方——只為留紀錄的放報告的 artifacts 資料夾，之後會再用的放 `scripts/` 或其他固定位置。（Seen：進度頁產生器與截圖腳本隨 scratchpad 消失，重寫一次。）**查證結果、研究整理這類之後還會再讀的文件也一樣**：一開始就寫進 repo 的 `docs/` 並從相關文件連過去，scratchpad 只放給 agent 的 brief。（Seen：Cloud Run 官方文件查證表存在 scratchpad，被說「有用的文件不應該在scratchpad」。）

## 跨 session

- **任務中途收到 peer session／subagent 的訊息，不代表任務結束**：處理完那則訊息就接著做原本的任務，不要回「No response requested」停下。工具呼叫失敗或被殺（exit 137、逾時）也一樣：改法重試（如改背景跑）或回報，不准默默停。（Seen：兩次在 peer 訊息後停住，我得打「?」；discord-dump 前景被殺後也停住，我得打「try」。）

## 開新 session

- **可以自己開新的本機 session**，不要回答做不到：把交接內容寫成 `docs/tasks/_handoff-<日期>-<主題>.md`，然後 `osascript` 叫 Terminal 執行 `cd <專案> && claude "$(cat '<交接檔>')"`（PATH 要含 `~/.local/bin`、nvm、Homebrew），開完用 `ListAgents` 確認新 session 出現。（Seen：使用者說「open new session and send msg to it」，先回做不到，被說「other session can do it, why you can't」。）
