# Cloudflare Worker 部署與維運

## 架構

- Worker：`amigurumi-weather-theme-server`
- R2 binding：`WALLPAPER_BUCKET`
- R2 bucket：`amigurumi-weather-wallpapers`
- 素材政策：手動上傳 PNG，不進行任何 AI 自動產圖
- PNG 上限：12 MiB

R2 key：

```text
wallpaper/<style>/<character>/<festival>_<city>_<character>_<period>_<weather>.png
```

## Secrets

必要：

```powershell
npx.cmd wrangler secret put MANUAL_UPLOAD_TOKEN
```

舊環境可暫時使用 `ADMIN_UPLOAD_TOKEN`，完成遷移後應刪除舊 secret。開發完成時撤銷手動上傳 token。

選用：

```powershell
npx.cmd wrangler secret put OPENWEATHER_API_KEY
npx.cmd wrangler secret put TELEGRAM_BOT_TOKEN
npx.cmd wrangler secret put TELEGRAM_CHAT_ID
```

Worker 不再讀取 `OPENAI_API_KEY`。確認部署穩定後，可在 Cloudflare 端刪除舊 `OPENAI_API_KEY` secret。

## 部署

```powershell
npm.cmd test
npm.cmd run cf:check
npm.cmd run cf:dry-run
npm.cmd run cf:deploy
```

本專案沒有 staging environment。正式部署前至少必須通過測試與 dry run。

## Admin Upload

Endpoint：`POST /admin/upload`

必要 multipart 欄位：

- `token`
- `city`
- `weather`
- `period`
- `character`
- `style`
- `image`

`image` 必須同時符合：

- MIME type 為 `image/png`
- PNG signature 正確
- 大小不超過 12 MiB

Worker 決定最終 object key。客戶端不得提供或覆寫 R2 path。

## 查詢行為

桌布查詢只執行 exact-key R2 lookup：

- 命中：回傳 PNG URL。
- 缺圖：回 `HTTP 304`，header `x-wallpaper-status=manual_wallpaper_missing_keep_current_wallpaper`。
- 不會呼叫 OpenAI、Workers AI 或其他產圖 API。

## 六時段 Cron

```toml
crons = ["0 4,9,11,16,21,23 * * *"]
```

排程依 Asia/Taipei 的六時段執行覆蓋率檢查。它使用 R2 `head()` 檢查高雄與台北、2 種畫風、5 種角色，共 20 個目前天氣／時段 PNG key；存在就跳過，缺少就記錄 `scheduled_wallpaper_coverage` 結構化 log。排程不寫入 R2，也不產圖。

若未設定 `OPENWEATHER_API_KEY`，排程以 `cloudy` 作為檢查天氣。

## Smoke Test

```powershell
Invoke-WebRequest -Uri "https://amigurumi-weather-theme-server.wemmei0130.workers.dev/health" -UseBasicParsing
```

預期：

```json
{"ok":true,"service":"weather-wallpaper-server"}
```

## 回滾

```powershell
npx.cmd wrangler versions list
npx.cmd wrangler rollback <VERSION_ID>
```

回滾版本若仍包含 OpenAI 產圖程式，即不符合目前的永久停用決策，不應作為長期版本。
