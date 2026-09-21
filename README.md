# 天氣動態桌布

目前版本：`4.37`

本專案由 Android 桌布客戶端、Cloudflare Worker 與 R2 組成。桌布素材一律由管理者手動產生並以 PNG 上傳；OpenAI Image API 自動產圖已永久移除。

## 目前架構

- Android App 根據城市、天氣、角色、畫風、節日與六個時段請求桌布。
- Worker 只查詢 R2；命中就回傳 PNG，缺圖則回 `HTTP 304`，手機保留現有桌布。
- Admin App 僅接受 PNG，上限 12 MiB。Token 只存在目前輸入欄位，不寫入 SharedPreferences。
- Windows 提示詞產生器只負責組合 Gemini／其他 AI agent 可用的提示詞，不具有 Admin 上傳或 API 產圖功能。
- GitHub 儲存庫保存程式碼與文字文件，不保存 APK。
- 私人 GitHub 不作為 App 自動更新來源；未來需要更新時，另將必要安裝檔放到公開發佈區。

## PNG 與 Android 動態桌布

PNG 本身是靜態圖片，但可以作為 Android Live Wallpaper 的背景。`DynamicWallpaperService` 會把 PNG 解碼成 `Bitmap`，持續繪製到 `WallpaperService` 的 Canvas，並在上方疊加雲、雨、霧、光點與其他動畫。因此 Android 接受的是 App 提供的動態桌布服務，而不是把 PNG 誤認為影片。

建議 PNG 規格：

- 直式 9:16。
- 建議 1024 x 1536 或更高直式解析度。
- MIME type 必須是 `image/png`，檔頭也必須是有效 PNG signature。
- 單檔不得超過 12 MiB。
- 上方保留時鐘、日期與狀態列閱讀空間。

## 六個時段

| 時段 | Asia/Taipei 時間 |
| --- | --- |
| `sunrise` | 04:00-06:59 |
| `morning` | 07:00-10:59 |
| `afternoon` | 11:00-15:59 |
| `sunset` | 16:00-18:59 |
| `night` | 19:00-22:59 |
| `midnight` | 23:00-03:59 |

R2 key 固定為：

```text
wallpaper/<style>/<character>/<festival>_<city>_<character>_<period>_<weather>.png
```

範例：

```text
wallpaper/knitted/cat/none_Kaohsiung_cat_sunrise_sunny.png
```

## 排程行為

Cloudflare Cron 在六個營運時間點執行。排程不產圖，只檢查高雄與台北目前時段、天氣下的 PNG 是否存在；已有適配圖就直接跳過，缺圖則寫入結構化 Worker log。每次檢查 2 個城市、2 種畫風與 5 種角色，共 20 個 R2 key。

## Secrets

必要：

```text
MANUAL_UPLOAD_TOKEN
```

相容舊名稱：`ADMIN_UPLOAD_TOKEN`。

選用：`OPENWEATHER_API_KEY`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`。

專案不再使用 `OPENAI_API_KEY` 或 `OPENAI_IMAGE_MODEL`。開發完成後應撤銷手動上傳 token。

## 提示詞

提示詞總表位於 [`prompts/README.md`](prompts/README.md)，機器可讀版本為 [`prompts/prompt-catalog.json`](prompts/prompt-catalog.json)。Windows 產生器位於 [`windows/WeatherWallpaperPromptGenerator`](windows/WeatherWallpaperPromptGenerator)，可根據任意城市、天氣、時段、節慶與畫風產生提示詞。已退役的 Worker OpenAI 提示詞僅保留歷史紀錄，不存在於 Worker 執行碼。

## 驗證

```powershell
npm.cmd test
npm.cmd run cf:check
npm.cmd run cf:dry-run
```

目前 Android 原始碼保留供既有手機使用，但此工作區沒有 Gradle wrapper、Java 與簽署 keystore，因此不宣稱可在乾淨環境重現 APK。後續主要服務將改由 Codex 在 Cloudflare 上重新架設 App server。
