---
title: improve：headless-shots 清理規則、report 規格驗收排序
date: 2026-10-24
session: 官網 V1 改版 (37de2c34-8782-4f7e-8bba-a15c85e3ce1c)
---

# 摘要

| Skill | 改了什麼 | 觸發的摩擦 |
|---|---|---|
| `headless-shots` | 設定檔放在自己的前綴下、每次退出刪除、一個 Chrome 截完所有圖；清理用 `pkill -f 'headless=new.<前綴>'` 取代過寬的 `--headless`；派 subagent 截圖時要傳這條規則 | 多個 subagent 自寫 CDP 腳本截圖：187 個殘留設定檔共 8 GB 把磁碟塞滿（寫檔 ENOSPC），71 個 headless Chrome 沒關，新 Chrome 起不來；原本的 pkill 會誤殺其他 session 的 headless Chrome |
| `report` | 新增準則 9：對照規格書驗收時照規格書順序與條目；會議紀錄併入對應條目並標「會議補充／會議修改」；使用者自己的後續優化另列一層 | 驗收報告先被分成「PDF／會議／優化」三層，使用者兩次修正：「PDF＋會議需求是一起的，會議是給予 pdf 的補充」 |

# 未進 skill 的部分

- 全域 `~/.claude/CLAUDE.md` Background agents 第 10 條：agent 暫存產物一律寫 scratchpad（截圖曾被寫進 repo 的 `web/v1/qa/`）。
- 專案記憶：實作 agent 變慢時才改由主對話統一驗證（使用者：「如果太慢才這樣做」）。
