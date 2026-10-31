# 提示詞匯出目錄

更新日期：2026-09-21

本目錄記錄專案內所有會組合成圖像生成提示詞的模板與片段。完整、機器可讀的版本位於 [`prompt-catalog.json`](./prompt-catalog.json)。

## 清單

| ID | 狀態 | 執行位置 | 原始程式 |
| --- | --- | --- | --- |
| `admin-manual-v1` | 目前主要流程 | Android Admin App，複製到 ChatGPT 手動產圖 | `MainActivity.buildAdminPrompt()` |
| `windows-agent-prompt-v1` | 目前可用工具 | Windows WPF 提示詞產生器 | `windows/WeatherWallpaperPromptGenerator/.../PromptBuilder.cs` |
| `worker-openai-v1` | 已退役，僅歷史紀錄 | 已從 Cloudflare Worker 執行碼移除 | 舊 `buildPrompt(scene)` 匯出內容 |
| `legacy-client-v1` | 舊版保留，目前未發現呼叫點 | Android 端舊 `PromptBuilder` | `PromptBuilder.build(scene)` |

專案沒有另外定義 chat system prompt、developer prompt 或 negative prompt API 欄位；排除項目直接寫在三套主提示詞內。

## 目前主要手動產圖模板

下列占位符由 Admin App 畫面資料與角色／風格片段替換：

```text
手機動態桌布插畫，直式 9:16，高解析度，溫暖可愛的童話氛圍。
{{style_prompt}}
City: {{city}}. Country: {{country}}.
Weather: {{weather}}. Time period: {{period}}. Temperature: {{temp_min}}C~{{temp_max}}C.
Landmarks: {{landmarks_csv}}.
Background融合 8 個當地知名景點，以微縮地景與童話城市的方式自然分布，不要像拼貼。
Use a distant wide-angle establishing view from a slightly elevated viewpoint, so landmarks are distributed naturally across the city scene with open sky and readable depth.
If the weather is sunny and hot, show soft golden sunlight, pale blue sky, fluffy white clouds, slight heat shimmer, tree shadows, and clear highlights.
{{character_prompt}}
Characters should look active and varied, with poses that imply motion and daily life instead of standing still.
Add subtle visual motion cues suitable for a live wallpaper background: drifting clouds, tiny boats on water, walking poses, fluttering awnings, falling rain or snow when weather requires it, wind lines, sparkling highlights, and lively daily movement.
Keep the upper sky area light, calm, open, and visually clean for phone time/date widgets.
Avoid text, logo, watermark, phone UI, clock, date, battery, signal icons, app labels, temperature widgets, large labels, and poster-like typography.
```

## 使用注意

- 目前主要營運流程是手動將 `admin-manual-v1` 貼到 ChatGPT 產圖，再由 Admin App 上傳 R2。
- `windows-agent-prompt-v1` 不呼叫 API；它要求具搜尋能力的 AI agent 先查證指定城市景點與地標、排除錯誤資料，再把完整清單納入同一幅 9:16 PNG 桌布構圖。
- Worker 自動產圖已永久移除；`worker-openai-v1` 只保留在提示詞目錄作歷史紀錄，不可作為備援執行路徑。
- 三套模板的景點數量規則不同：Admin 寫 8 個；Worker 寫 2 到 4 個；舊版手機模板使用場景資料中的完整清單。這是現況紀錄，不在本次匯出中改寫。
- 本目錄不得加入 API key、Cloudflare secret、GitHub token 或 Admin upload token。
- 修改程式內提示詞時，應同步更新 `prompt-catalog.json`，避免文件與實際行為分歧。
