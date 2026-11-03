# improve：Discord 頻道匯出腳本收進 dev-skills

| | 之前 ❌ | 之後 ✓ |
|---|---|---|
| 抓 Discord 頻道 | 瀏覽器捲動虛擬化列表，#pimi 只抓到 130／1004 則 | `bin/discord-dump.py`，bot API，1004 則含 4 個討論串 |
| 腳本位置 | 埋在 `dodo/docs/workflow-inventory/_pipeline/`，別的專案找不到 | `dev-skills/bin/`，全域 CLAUDE.md 有指向 |
| create-tasks Chat-app source | 只有瀏覽器 accessibility tree 一條路 | Discord 先跑腳本，失敗才退回瀏覽器 |

## 摩擦

使用者要求下載 #pimi 訊息，agent 直接用瀏覽器捲動；使用者兩度提醒「我們寫過腳本」才找到 dodo 的 `dump_discord.py`。

## 改動

- 新增 `bin/discord-dump.py`：單頻道＋討論串、`--after` 日期過濾、已封存討論串分頁、論壇頻道、附件網址／嵌入標題／回覆對象；token 讀 Keychain `discord-bot-token`，退回 `$DISCORD_BOT_TOKEN`。
- `skills/create-tasks/SKILL.md`：Chat-app source 加 Discord 優先用腳本。
- `~/.claude/CLAUDE.md`（不在本 repo）：加 `### Discord` 一行。

## 驗證

- #pimi 全量：1004 則，輸出與先前匯出逐字相同（除匯出時間行）。
- `--after 2026-11-01`：8 則。
- 論壇頻道、封存討論串 >100 的分頁：未實測。
