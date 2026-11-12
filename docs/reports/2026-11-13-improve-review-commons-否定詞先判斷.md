---
session: 2026-11-12-demo-final-collapse-satisfaction (3bc9a4af-24e8-4853-9428-cb7e8179a2e4)
---

# improve：review commons 加「自由文字意圖比對先判斷否定」

| | 改前 ❌ | 改後 ✓ |
|---|---|---|
| shared/review/commons.md | 沒有這條規則 | 新增一條：用關鍵字或正則比對自由文字的意圖時，先判斷否定詞和抱怨詞，再判斷肯定詞 |

## 起因

sontis demo ⑥ 組片的打字回覆用關鍵字比對。「第 2 場不滿意」裡面含有「滿意」，結果被判成滿意，影片直接完成。這個問題是 Codex quick-review 抓到的（WR-03），已在 sontis-ai e8be3ee 修好。

## 變更

`shared/review/commons.md` 的 `## Added by /improve` 加了一行。之後每次 review 都會檢查這件事。

另一項提案是 wrap-up 在 worktree session 合併的流程，使用者選擇略過。
