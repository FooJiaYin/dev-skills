// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["sync"] = {
  "id": "sync",
  "chapter": "prepare",
  "title": "今天開工，先接上同事昨天的進度",
  "intro": "大家同時在改程式，手上的版本很容易慢半拍。它會先看看本地有沒有還沒收好的工作，再接上同事的最新進度；遇到衝突就停下來，不會替你猜哪一邊該留下。",
  "input": "GitHub 上的團隊進度＋本地修改",
  "output": "GitHub／工作分支",
  "artifact": "✓ 同步完成\n你在 branch: feat/stock-reservation\n已併入: origin/feat/stock-reservation / main / 對方 branches（feat/product-list）\n已 push: 是\n工作目錄: 乾淨，可以開工",
  "why": "開工不等於直接覆蓋本地。自己的工作要先保住，有衝突也不硬猜。",
  "routes": [
    "github"
  ],
  "steps": [
    "檢查本地",
    "取得並合併",
    "同步回 GitHub"
  ],
  "messages": [
    [
      "user",
      "/sync"
    ],
    [
      "skill",
      "/sync"
    ],
    [
      "tool",
      "Git · 檢查分支、未提交修改與是否有進行中的合併"
    ],
    [
      "assistant",
      "你手上沒有還沒收尾的修改，我先拿最新進度。"
    ],
    [
      "tool",
      "Git · 取得遠端更新，依序合併主分支與隊友近期分支"
    ],
    [
      "assistant",
      "商品列表的更新接進來了，沒有衝突。接著把合併後的進度同步回 GitHub。"
    ],
    [
      "tool",
      "Git · 推送同步結果"
    ],
    [
      "assistant",
      "好了，可以開始預留功能。若剛才有未提交修改，我會先請你用 /wrap-up Quick 收好；如果合併衝突，就會停下來請 reviewer 協助。"
    ]
  ]
};
