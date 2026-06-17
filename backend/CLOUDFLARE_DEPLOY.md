# Cloudflare Worker 部署與維運 Runbook

本專案後端使用 Cloudflare Worker + R2，Worker 程式入口：

`backend/amigurumi-theme-server-worker.js`

## 目前線上架構

- Worker name: `amigurumi-weather-theme-server`
- R2 bucket: `amigurumi-weather-wallpapers`
- R2 binding: `WALLPAPER_BUCKET`
- R2 object key:
  `wallpaper/<style>/<festival>_<char>_<loc>_<period>_<weather>.mp4`
- 注意：目前 key 保留 `.mp4` 相容命名，但 payload 是 OpenAI Image API 產生的 PNG image。API response 會回：
  - `content_type: image/png`
  - `asset_kind: generated_image`
  - `animation.payload_content_type: image/png`

## Worker Secrets

所有敏感值都必須用 Cloudflare Worker secrets，不可寫在原始碼或文件中。

必要：

```powershell
npx.cmd wrangler secret put OPENAI_API_KEY
```

選用，但建議設定：

```powershell
npx.cmd wrangler secret put OPENWEATHER_API_KEY
npx.cmd wrangler secret put TELEGRAM_BOT_TOKEN
npx.cmd wrangler secret put TELEGRAM_CHAT_ID
```

用途：

- `OPENAI_API_KEY`: R2 cache miss 時呼叫 OpenAI Image API。
- `OPENWEATHER_API_KEY`: 舊版手機端 `lat/lon` 天氣查詢相容路由使用。
- `TELEGRAM_BOT_TOKEN`: OpenAI 失敗、每日生成上限等事件告警。
- `TELEGRAM_CHAT_ID`: Telegram 告警接收對象。

非敏感 vars 由 `wrangler.toml` 設定：

- `OPENAI_IMAGE_MODEL`
- `MAX_DAILY_GENERATIONS_PER_CITY`
- `PUBLIC_WORKER_ORIGIN`

## 部署

確認登入：

```powershell
npm.cmd run cf:whoami
```

建立 R2 bucket：

```powershell
npm.cmd run cf:create-bucket
```

部署 Worker：

```powershell
npm.cmd run cf:deploy
```

部署後查看即時 log：

```powershell
npm.cmd run cf:tail
```

## Smoke Test

健康檢查：

```powershell
Invoke-WebRequest -Uri "https://amigurumi-weather-theme-server.wemmei0130.workers.dev/health" -UseBasicParsing
```

不觸發 OpenAI 的 cache hit 測試需要 R2 已有對應 object。一般查詢範例：

```text
https://amigurumi-weather-theme-server.wemmei0130.workers.dev/?loc=高雄市&weather=Thunderstorm&period=Night&char=cat&style=針織
```

如果 R2 miss 且 OpenAI 失敗或達每日上限，Worker 會回 `HTTP 304`，手機端應保留最後一張桌布。

## SRE 防線

- R2 exact key cache hit: 不呼叫 OpenAI，費用為 0。
- R2 lock: 同一張圖正在生成時，其他請求回 304，避免並發重複生成。
- Daily limit: 同 city/style 每日生成量受 `MAX_DAILY_GENERATIONS_PER_CITY` 限制。
- OpenAI timeout: 55 秒。
- Telegram timeout: 10 秒。
- Telegram alert 使用 `ctx.waitUntil()`，且有 catch 防止背景 promise 失控。
- `/files/...` 只允許讀取 `wallpaper/` prefix。

## Cron 狀態

`wrangler.toml` 目前保留 cron：

```toml
crons = ["0 4,9,11,16,21,23 * * *"]
```

目前 `scheduled()` handler 只寫入 heartbeat log，不會自動呼叫 OpenAI 生成圖片，以避免排程造成非預期費用。未來若要做預生成，需先設計城市/時段/每日上限與告警策略。

## 回滾

列出版本：

```powershell
npx.cmd wrangler versions list
```

回滾請在 Cloudflare Dashboard 或 Wrangler 版本管理中選擇前一個穩定版本。回滾前先確認該版本對應的 R2 key 格式與手機端版本相容。

## Admin Upload 狀態

新版 Worker 已清空舊 `/admin/upload` 架構，目前沒有提供 manual upload endpoint。Android admin APK 中若仍使用 `/admin/upload`，會需要後續重新接上新版安全上傳流程。

安全原則：

- admin APK 不上傳 public GitHub release。
- token-bearing admin APK 僅本機保存或私有渠道。
- public APK 與 admin APK 分開輸出。
