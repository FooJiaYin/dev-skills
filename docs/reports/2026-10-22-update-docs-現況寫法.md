# update-docs：文件改寫為現況，不加變更註記

| | 改前 ❌ | 改後 ✓ |
|---|---|---|
| §5 寫法 | 就地編輯＋旁邊加 `_(日期: …)_`／`<!-- 日期 -->` marker | 就地改寫成現況，不加任何日期／變更註記 |
| 碰到舊 marker | 保留 | 所在段落一併改成純現況敘述 |
| 歷程放哪 | 文件內 marker | report 與 commit message |

## 起因

sparktoy-erp 上架 L01–L06 wrap-up 時，`/update-docs` 依 §5 提案在 spec／schemas／AGENTS.md 加日期 marker，使用者回「update 不要太像 log，docs 保留 document 最新狀態就好」。疊在舊文上的 `[Changed]`、刪除線、「10-14：補…」讓讀者自己拼現況，與 §5 原本反對「尾端 updates 段」的理由相同。

## 變更

- `skills/update-docs/SKILL.md` §5：改名「rewrite in place as current state」；列出禁止的 marker 形式；觸及段落順手清掉舊 marker；保留「新標題放正確位置、不加尾端 updates 段」。

Session: feat/listing-workbench-and-platform-export (9a6419d8-087b-448a-8b97-89a257c90c89)
