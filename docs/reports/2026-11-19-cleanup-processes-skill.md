---
session: improve-fanout前規劃驗證 (08b4fd52-4070-4822-ac37-a9f1ab1c957b)
---

# cleanup-processes：檢查當下的程序、關掉沒人用的

# Description

- 起因：使用者跨 3 個專案說過 5 次「很慢」「關掉不用的」（10/28 meetmeoffline、11/17 sparktoy、11/18 pimi 兩次、11/19），每次都重新摸索。11/19 這次查到三台開了一週的孤兒伺服器，以及一台保留 8 GB、裡面只用 400 MB 的 Docker VM。
- 討論過放哪裡：在 `agents-and-sessions.md` 加幾句、寫成 hook、寫成 skill。定為 skill，理由是七種會用到的情況只有兩種會讀到那份 md（使用者直接說「很慢」的五次都不在派 agent 的當下）。
- 使用者的要求：不內建「要找哪幾種東西」的清單（上次是 Chrome、這次是 Docker），每次從當下有哪些 process 看起。

# Changes Made

| 檔案 | 內容 |
|---|---|
| `skills/cleanup-processes/SKILL.md`（新，36 行） | 判斷訊號、三級處理（直接關／問／不碰）、怎麼關與怎麼接回來、兩個坑；`Runs on:` 一行 |
| `skills/cleanup-processes/scripts/check.py`（新，唯讀） | 總覽、同類合併的實際佔用排行（含被壓縮的記憶體）、Claude session 清單與狀態、在聽 port 的程序與歸屬、容器／VM、三級候選建議；`--json` |
| `README.md` | 工具表加一列、`<skill-name>` 安裝清單加一項 |
| `docs/agents-and-sessions.md` | 監看那條：「跑得比平常慢很多時才看機器資源，不用定時查」，指向這個 skill |
| `skills/wrap-up/full.md` §6 | 清理步驟也要關掉本 session 開過的 server、瀏覽器、容器 |
| `AGENTS.md`〈Skills〉 | 新增第 3 條：每次改 skill 都要檢查並寫明在 Codex、另一台機器、其他 OS 能不能跑 |
| `TODO.md` | 四條（見下） |

# Updates（審查後修掉的）

quick-review（Codex 兩輪＋逐行讀）找到的問題，全部往保守方向修：

| 問題 | 修法 |
|---|---|
| Windows 上 `os.kill(pid, 0)` 會對 session 送 Ctrl+C | 非 macOS 不做任何探測，印說明後結束 |
| 孤兒伺服器「比所有活著的 session 早開」就列為可直接關；session 重開過、在 worktree、或 Codex 開的都會判錯，沒有活著的 session 時 `all([])` 為真 | 孤兒伺服器一律「問」 |
| 帶自動化參數的孤兒瀏覽器直接關，但可能還有 session 連著除錯 port | 確認沒人連著才直接關，查不出來就問 |
| 容器裡的資料庫在主機上只是一個 port forwarder，不受資料庫規則保護 | forwarder 一律不碰 |
| 探測失敗時整張表顯示「(無)」，讀起來像沒有可關的 | 最前面印失敗清單；ps／top 失敗時候選表印「資料不足，無法歸類」 |
| 閒置 ≥1 小時的 session 直接關，底下的伺服器跟著死 | 維持直接關（使用者的決定），每列列出底下在聽 port 的子程序 |

# Result

**驗證**（都用 `/usr/bin/python3` 3.9.6）

| 檢查 | 結果 |
|---|---|
| 正常實跑 | exit 0，六節有內容；自己、使用者的 Chrome、postgres、busy 的 session 在「不碰」；三台 7 天的孤兒伺服器在「要問」；「可直接關」為空 |
| `PATH=/nonexistent` | exit 0，最前面列出失敗的探測，候選表為「資料不足」 |
| `HOME` 指到空資料夾 | exit 0，sessions 節寫「找不到 Claude Code 的 session 資料」 |
| 模擬 linux／win32（把 `os.kill` 換成會丟例外的函式） | 只印說明，`os.kill` 沒被呼叫 |
| 除錯 port 連線判斷 | 用自己開的 socket＋子程序測：連著時列得出、斷開後為空 |

**Runs on**

| 環境 | 狀況 |
|---|---|
| macOS＋Claude Code | 完整 |
| 另一台 Mac | 可以；沒有 colima／docker 時略過那一節；不認得 Docker Desktop |
| Codex | 程序與 port 兩段可以；session 清單只列得到 Claude Code 的 |
| 其他 OS | 腳本印說明後結束；agent 用該系統的工具自己看，訊號與三級照用（使用者：「看著辦」） |

**第一次實跑時這台機器的狀況**：關掉 10 個閒置超過一小時的 session 與 Docker VM 後，swap 從 16.5 GB 降到 6.5 GB。

# Unsolved Issues

都在 `TODO.md`：

- 三個分支沒在真的程序上跑過：孤兒自動化瀏覽器、colima 開著時的 VM 對照與 forwarder、閒置 ≥1 小時的 session。
- 審查的小項沒修：瀏覽器自動化 MCP 那一列每次都出現在「問」（雜訊）、不認得 Docker Desktop、`top -n 400` 的上限、`$HOME` 邊界。
- 同一個 session 加的 `[agent]` session-log hook 只手動設在這台的 `~/.claude/settings.json`，安裝文件沒有記載。
- 延後：`[proc]` 紀錄、SessionEnd 關自己開的、swap 門檻提醒、主對話慢指令的紀錄。
- 這台機器上三台孤兒伺服器（8765／8790／8791）還沒關：auto mode 擋了 `kill`。
