# 開 subagent、開 session、跨 session 協作

派 subagent、開新 session、或跟其他 session 協作之前先讀這份。防睡、背景等待結束就接著做、收到 peer 訊息不代表任務結束這三條同時留在 `~/.claude/CLAUDE.md`（隨時都要遵守）。

## 派 agent 之前

- 防睡由 hook（`dev-skills/bin/keep-awake.py`）處理：派 agent 時自動 caffeinate 2 小時，Remote Control 時撐到 session 結束。**不要自己開或 kill caffeinate，絕不 `pkill`／`killall caffeinate`**（會殺掉使用者和其他 session 的）。
- **Fan-out 前 `ls` 確認每個共用輸入（指示檔、資料檔）都在**；共用指示檔不要放在會被重建腳本清空的資料夾（seen：重建腳本 `rm *.md` 連指示檔一起刪，17 個 agent 空跑）。
- **fan-out 之前，先規劃這批 agent 的驗證怎麼進行最有效率，寫進 brief。** 驗證包含測試、型別檢查、build、dev server、瀏覽器截圖。做法因案而異，不要照搬上一次的解法；至少想過：
  - 成本花在哪、哪些會被重複付（每個測試檔重啟一次服務、每條測試重建一次資料、每張截圖重開一次瀏覽器、同一套測試被好幾個 agent 各跑一遍）。第一次用某個測試工具時，先讀它的說明，看它怎麼隔離與共用資料。
  - 誰跑：各 agent 只跑自己改的檔、**指定一個專門跑驗證的 subagent**（全部交件後跑一次整套，只回報一張結果表：過幾條、哪幾條失敗、各屬於誰）、或主對話自己跑。主對話跑會佔用 context，使用者沒辦法同時討論別的事；要空出主對話就用驗證 agent。
  - 同時幾份、這台機器撐不撐得住（`sysctl -n hw.memsize vm.swapusage`、`uptime`；swap 已用掉好幾 GB 就先減少或請使用者關掉其他程式）。
  - 在 agent 的環境與權限下跑不跑得了（`node_modules` 在不在、migration 套了沒、auto mode 會不會擋）。
  - 集中驗證之後確認真的有人驗，不要變成沒人驗。
  - Seen（各次出事的點都不同，共同點是派出去之前沒規劃）：pimi 11/17——8 GB 機器同時 4–6 個 agent 各跑整合測試再加本機映像 build，swap 12 GB、同一支測試從 2 分鐘變 11 分鐘、資料庫當掉；後來四個 agent 各跑一份整套單元測試，每份 34–45 分鐘，使用者說「直接大家一起跑一測試如何」，改成只跑一次後整輪 11 分鐘；38 個測試檔寫完才去讀測試工具說明，35 個是每條重建資料。meetmeoffline 10/23——每個 agent 自己起 server、自己截圖，驗收 agent 截 68 張、每張重開 Chrome，使用者問「為什麼每個agent要做那麼久？」「驗證你可以派另外一個agent負責，或是自己做」。meetmeoffline 10/28——5 個檢查 agent 各開一台 dev server，使用者說「verify 太久了」「現在整台電腦很慢」「一次跑一個agent就好」；同日另一個 session 說了集中驗證，結果主對話也沒截圖，畫面問題是使用者自己抓到的。sparktoy 10/22——worktree 沒有 `node_modules`，三個 agent 都以未驗證交件。反例（brief 先寫清楚驗證範圍，沒出事）：meetmeoffline 10/28 工作人員後台「只跑 `tsc -b`，不起 dev server、不截圖」；poolgress 9/5、9/6「pytest 最多跑兩次」「只跑自己的測試檔、最多修兩輪、不跑整包」。
- **跑很久的指令，輸出先存成檔再篩選**（`cmd > log 2>&1; grep … log`），不要直接接 `| grep … | head`：`head` 先吃滿就看不到結尾的結果，等於白跑。（Seen：一支 10 分鐘的測試接了 `grep … | head -8`，摘要行被前面 8 行雜訊擠掉，結果未知只能重來。）
- **要 agent 產出長檔時，prompt 一律寫明「分段寫入：先 Write 前段，之後每段用 Edit 追加；每欄精簡在一行」**。一次 Write 整份長輸出會 API 逾時，或 20–40 分鐘無動靜看似卡死。判斷卡住要看輸入規模與同批其他 agent 的耗時，不要只看時間（seen：誤判卡住而重派，原 agent 隨後正常交件）。
- **Subagent 模型：不要用 Fable。** 抽取、分類、歸納用 `sonnet`；需要判斷與綜合的撰寫用 `opus`。先派 1–2 個試跑確認品質再全量派出。
- **Fan-out prompt 寫明「不要再派 agent，自己依序做完」。** 子 agent 回報「未完成」時，先用 `ListAgents` 看它派出的子 agent 是否還在跑，再決定接續或重派（seen：兩組交回未完成，其子 agent 其實還在跑，叫它重做差點雙寫同一批檔）。回報進度一律 `ls` 輸出檔來數，不憑記憶。
- **WebSearch 整個 session（主對話＋所有子 agent）共用 200 次，文件未記載、無設定可調；WebFetch 不受限。** 研究型 fan-out 前先估「系統數 × 約 20 次」，超過就分到不同 session 跑，或在 prompt 直接給文件網址讓 agent 用 WebFetch。
- **派實作 agent 前，把任務 `# Context`／會議裡每一條具體的 UI 要求（放哪裡、長怎樣、用語）逐字抄進 prompt 當驗收條件；交回時逐條核對（用 `/align end`），沒做到的直接告訴我。** 只寫邏輯不寫位置，agent 會放在它覺得方便的地方。（Seen：會議寫「參數介面將類似現有稅費係數欄位」，prompt 只寫換算規則，利潤率被塞進每個公式的「編輯」步驟表，我問「為什麼沒看到利潤input？在哪裡」才發現。）
- **agent 要寫呼叫外部 CLI 的程式時，brief 裡貼上已驗證的指令與 `--help` 片段**；沒驗證過的旗標組合在整合時實跑一次，不要讓 agent 猜。（Seen：quick-review 的 `run.py` 假設 `codex exec review --uncommitted` 可帶 prompt，實跑才發現不行。）
- **brief 要 agent 跑某個 skill 時，寫 brief 之前先自己讀過那個 skill**，brief 裡的限制不得和 skill 的規定衝突；要偏離先問使用者。（Seen：為了「不要在共用 dev 上 commit」，brief 寫了「截圖不上傳」，蓋掉 sync-report 規定的圖片上傳，四張票只有文字，使用者問「為何」才補傳 60 張圖。）
- **brief 一律要求邊做邊落地**：每完成一步就寫出來——程式碼每個修正各自 commit、結果逐步附加到 repo 裡的檔案（不是最後一次寫整份），並維護一份進度檔（做完哪一步、下一步是什麼），讓 session 重啟後接得回來。（Seen：一個 session 重啟四次，瀏覽器測試、review 修正、角色驗證的 agent 都被殺，前三次產物只在 scratchpad 或還沒寫出，全部重跑；改成逐步 commit＋進度檔後才接得回來。）
- **要 agent 做瀏覽器實測或存測試資料時，前置由主對話做完再派。** auto mode 會擋 subagent 起 dev server、對共用本機 DB 存檔、複製檔案進 `node_modules`，而且是做到一半才擋。派之前：① 確認 worktree 的 `node_modules` 齊全（從主 checkout `cp -cR` 後 `ls` 一個晚裝的套件）；② 主對話自己把 dev server 起好（被擋就請使用者切 default mode 或自己跑），brief 寫明 port；③ brief 逐項寫明**可以寫哪些測試資料**（哪幾件商品、能不能新增），不要一句「不准寫 DB」之後又要它存檔實測。（Seen：三個 agent 分別卡在補套件、存測試商品、起 dev server，review 修正後的角色存檔實測兩度沒做成，PR 只能停在 draft。）

## agent 執行中與交件

- **使用者中斷（Esc）與 `/compact` 會停掉所有背景 agent**，被停的不能 SendMessage 接續、也不能自行重派（要使用者明說）。中斷或 compact 之後，先核對預期的輸出檔是否存在、`tasks/<id>.output` 的 mtime 是否還在動，不要空等通知。要重派時，先用腳本從 `tasks/<id>.output`（JSONL）抽出 `thinking` 區塊的尾段約 2 萬字存成草稿，連同原始輸入給新 agent 接續——不要自己讀那個檔（會爆 context）。API 逾時失敗的 agent 則先試 SendMessage 接續，不要直接重派。
- **派出 agent 時先估它要多久，並告訴使用者；派出後定時看有沒有太慢或卡住，超過估計的兩倍還沒交件，就查它最後一個事件，回報一行現況，不要空等通知。** 用腳本從 `tasks/<id>.output`（JSONL）列出每個 tool call 的時間、名稱與有沒有拿到結果（不要自己讀整個檔）。分三種情況：① 最後一個事件是「送出指令、還沒有結果」→ 先當成**在等權限提示**（讀寫工作目錄以外的路徑最常見），馬上告訴使用者「有權限提示在等你」，不要砍掉；② 指令本身在跑（測試、build）→ 回報它在跑什麼；跑得比平常慢很多時才去看機器資源（`sysctl -n vm.swapusage`、`uptime`，不用平時定時查），不夠用就停掉最吃資源的那一份、關掉沒在用的 server 或容器（做法見 `cleanup-processes` skill），並告訴使用者；③ 結果早就回來、模型卻沒有下一步 → 才算停滯：停掉它，小任務主對話自己做，大任務用更窄的 brief 重派。沒有 agent 交件的期間，每隔一段時間也主動回報一次。**brief 不要叫 agent 去讀工作目錄以外的東西**（上層資料夾的 SOP、Homebrew 目錄、別的 repo）：主對話先讀好，把需要的段落貼進 brief。agent 結束後 session log 的 `[agent] done … slowest=…` 會記下最慢的那一步。（Seen：改四份部署文件的 agent 跑了兩個半小時只做 11 個動作，使用者問「在幹嘛」「他已經兩個小時了耶」才發現，當下判斷成停滯而砍掉；事後對時間，兩次等待各 55、91 分鐘，都是讀工作目錄以外的路徑，結果回來的時間正好是使用者回到電腦——推論是在等權限。同一個 session 使用者另外問了「怎麼那麼久」「太久了」「？」，其中一次主對話已沉默 74 分鐘。）
- **背景等待（deploy、build、CI）一結束就接著做下一步並回報，不要停下來等我提醒。** 同時輪詢多件事時，別讓慢的（GHCR build）擋住快的（Vercel 已 READY）該做的驗證；已核可的下一步直接做。（Seen：Vercel 正式部署早就好了，卻等到我打「ready」才驗證，被說「you should not wait for me to remind you it's complete」。）
- **agent 的暫存產物（截圖、量測用的臨時頁面、草稿）一律寫在 scratchpad，不准寫進 repo 工作目錄**；brief 裡寫明輸出路徑。交件後 `git status` 檢查有沒有冒出不明檔案。（Seen：截圖被寫進 `web/v1/qa/`、效能比對頁 `_perf-before.html` 放在網站資料夾，另一個 session 打包部署時差點一起帶上去。）使用者要的交付檔（xlsx、匯出檔、範例檔）不是暫存產物，不放 scratchpad：放在使用者找得到、跟用途相符的位置（例如專案旁的資料夾、對應文件的 artifacts 資料夾或 `~/Downloads`），給絕對路徑；scratchpad 只放產生它的中間腳本。（Seen：WACA 範例 xlsx 放 scratchpad，被說「output should not save in scratchpad」。）**session 重啟會清空 scratchpad**：會反覆重跑的產生腳本（報告頁、截圖腳本）一開始就放對地方——只為留紀錄的放報告的 artifacts 資料夾，之後會再用的放 `scripts/` 或其他固定位置。（Seen：進度頁產生器與截圖腳本隨 scratchpad 消失，重寫一次。）**查證結果、研究整理這類之後還會再讀的文件也一樣**：一開始就寫進 repo 的 `docs/` 並從相關文件連過去，scratchpad 只放給 agent 的 brief。（Seen：Cloud Run 官方文件查證表存在 scratchpad，被說「有用的文件不應該在scratchpad」。）

## 跨 session

- **任務中途收到 peer session／subagent 的訊息，不代表任務結束**：處理完那則訊息就接著做原本的任務，不要回「No response requested」停下。工具呼叫失敗或被殺（exit 137、逾時）也一樣：改法重試（如改背景跑）或回報，不准默默停。（Seen：兩次在 peer 訊息後停住，我得打「?」；discord-dump 前景被殺後也停住，我得打「try」。）

## 開新 session

- **可以自己開新的本機 session**，不要回答做不到：把交接內容寫成 `docs/tasks/_handoff-<日期>-<主題>.md`，然後 `osascript` 叫 Terminal 執行 `cd <專案> && claude "$(cat '<交接檔>')"`（PATH 要含 `~/.local/bin`、nvm、Homebrew），開完用 `ListAgents` 確認新 session 出現。（Seen：使用者說「open new session and send msg to it」，先回做不到，被說「other session can do it, why you can't」。）
- **開新 session 時就命名、指定 id**：`claude -n "<YYYY-MM-DD>-<主題>" --session-id "$(uuidgen | tr A-Z a-z)" "$(cat '<交接檔>')"`，把 id 和名稱記在交接檔與回報裡，事後不用猜誰是誰（`-n` 會顯示在提示框、`/resume` 清單與終端機標題）。ListAgents 只顯示 `<專案>-xx`，跟 `-n` 名稱是否連動未驗證；要發訊息時，交接檔開場加一句「開工前用 SendMessage 告訴 `<我的 ListAgents 名稱>` 你的 ListAgents 名稱」來對上；**寫交接檔前先自己 `ListAgents`，把自己的名稱與 `[ref]` 實際填進去，不要寫「找名稱含 `<專案>` 的另一個 session」**（seen：同專案有 7 個 session，接手方只能猜，報到與交付訊息都沒人回）。（Seen：商品圖片、報價單、9–10 月匯入三個 session 分不出誰是誰，同一則訊息發給兩個，其中一個回「不是我」。）
- **交接檔裡的待決定項，接手後開工前就問。** 接手 session 讀完交接檔，把標成「待確認／拿不準就寫 TODO」的項目先用 `AskUserQuestion` 問掉，同時做不受影響的部分；不要留到 wrap-up 才問。寫交接檔的一方也寫明 wrap-up 用 Quick 還是 Full。（Seen：交接寫「台幣成本人工覆寫要不要給按鈕，拿不準就寫 TODO」，接手 session 做完、實測完才問，使用者選要做，多一輪實作與實測。）
