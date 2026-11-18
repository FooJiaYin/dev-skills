# improve：開新 session 時命名並指定 id（2026-11-18）

Session：sparktoy 第一階段驗收盤點（9e7ca66e-a1ec-4618-b2a2-4596462da111）

## 摩擦

用 osascript 開或 resume 了好幾個 session：商品圖片、報價單、9–10 月匯入、狼王、批量更新。ListAgents 只顯示 `sparktoy-xx`，對不出是哪個 session id。結果同一則訊息發給兩個 session，其中一個回「不是我」；報價單分支也一度以為沒人負責。

## 修改

`docs/agents-and-sessions.md`〈開新 session〉加一條：

- 開的時候用 `claude -n "<日期>-<主題>" --session-id "$(uuidgen | tr A-Z a-z)"`，把名稱和 id 記在交接檔與回報裡。
- ListAgents 名稱是否跟 `-n` 連動未驗證。需要發訊息時，交接檔開場請新 session 先回報自己的 ListAgents 名稱。

使用者的提議：「開新session既然都知道他要做什麼，是不是可以類似先rename session」。

## 同時改了（不在本 repo）

`~/.claude/CLAUDE.md` gcloud 第 4 條：只是唯讀查 prod，也可能被 auto mode 擋，先請使用者切 mode。
