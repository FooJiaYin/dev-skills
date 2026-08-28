# ERP UI 風格方向（sparktoy-erp，2026-08-26）

同一頁「產品資料列表」的四種風格 artboard，供之後建其他 ERP 時參考。格式為 Claude Design `.dc.html`（用 `/design` skill 的 seed-canvas.mjs 可重新組成畫布）。

| 檔 | 方向 | 重點 |
|---|---|---|
| `Current.dc.html` | 現況 baseline | neutral 灰、Arial、底線文字動作（反面教材） |
| `Main.dc.html` | **B Refined Neutral（sparktoy 選用）** | Noto Sans TC、slate 底 + indigo 主色、側欄 active、pill 狀態、icon 列動作 |
| `OptionC.dc.html` | C 品牌暖色 | 深色側欄、橘色 accent、stone 暖灰、56px 商品圖兩行品名 |
| `OptionD.dc.html` | D 高密度工作台 | 60px icon rail、32px 列高、成本/售價/毛利率、勾選+批次列、密度 tweak |
| `ProductForm.dc.html` | B 套在密集表單 | 五區塊表單的密度壓力測試；禁用欄實色灰、試算值 dashed 標示 |
| `Login.dc.html` | B 登入頁 | 一般／錯誤兩狀態並排、focus ring 示範 |

Token（B）：bg `#f8fafc` / surface `#fff` / control border `#cbd5e1` / divider `#e2e8f0` / text `#0f172a #475569 #64748b #94a3b8` / accent indigo-600 `#4f46e5`（soft `#eef2ff`, text `#4338ca`）/ radius card 12 · control 8 · pill 999。
