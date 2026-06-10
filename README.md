# codex_AI_lab

## Amigurumi Weather Theme

Amigurumi Weather Theme 是 Android 動態桌布 App。v1.5 開始採用 server 與手機端分工：

- Server 端負責天氣查詢、判斷地點/天氣/天色是否已有桌布、產生新桌布、儲存桌布檔案。
- 手機端負責取得 GPS 或自訂城市、向 server 提出桌布需求、下載相對地區桌布、套用靜態桌布與 Live Wallpaper。

## 目前版本

- App package: `com.codex.amigurumiweather`
- Version: `2.2`
- Min SDK: 26
- Target SDK: 36
- 通用 APK: `outputs/AmigurumiWeatherTheme-v2.2-universal-debug.apk`
- Samsung U23/S23 APK: `outputs/AmigurumiWeatherTheme-v2.2-samsung-u23-debug.apk`

## 手機端功能

- 可使用 GPS 自動定位，也可手動指定城市。
- App 畫面只保留地點設定、語言設定、桌布操作、更新按鈕與版本資訊。
- Theme server、天氣 API、OpenAI、model、更新間隔等參數都改為隱藏預設值。
- 手機端會用隱藏預設 server 查詢或建立桌布。
- 手機端偵測 server 有新桌布時會下載、儲存並套用。
- Live Wallpaper 會使用 server 回傳的背景圖，再依天氣疊加動態雨、雲、霧等效果。
- 手機離線或 server 連線異常時，保留最後一張已下載的動態桌布，並在 App 顯示連線異常訊息。
- 手機端只保留最新一張動態桌布檔，更新成功後會清理舊桌布暫存，避免佔用過多儲存空間。
- 桌布留白處會顯示明顯但不衝突的地名；在台灣用本地地名，在外國用英文。
- 動態桌布會由手機端固定疊加地名，即使 server 產生的背景漏掉地名也會顯示。
- AI 生成背景時會要求把地名放在較淡、乾淨的天空部位，避免與建築、人物、雲雨或鎖定畫面資訊重疊。
- App 內 `Check app update` 會從 GitHub Releases 依手機型號下載合適 APK。
- 若 GitHub 最新版本不高於目前安裝版本，`Check app update` 只會顯示已是最新版本，不會下載或開啟安裝流程。

## Server 端功能

範例檔案：

```text
backend/amigurumi-theme-server-worker.js
```

此 Cloudflare Worker 同時負責：

- OpenWeather 天氣代理。
- OpenAI 產生 Amigurumi 城市桌布。
- Cloudflare R2 儲存桌布 PNG 與 manifest。
- 依 `地點 + 天氣 + 天色` 建立 scene key。
- 若 server 已有符合 scene key 的桌布，直接回傳既有檔案。
- 若沒有符合桌布，就產生新圖並儲存。
- Cloudflare Cron 會每 30 分鐘追蹤預設城市高雄與台北，依天氣與天色預先生圖。
- 其他 GPS 或自訂地點仍會在手機提出需求時即時查詢/產圖。
- Server 端產生的桌布與 manifest 只保留 1 日，超過保留期會自動清理。

## 檔名規則

Server 端新產生的桌布會使用：

```text
city_YYYYMMDD_VVV.png
```

範例：

```text
kaohsiung_20260610_001.png
kaohsiung_20260610_002.png
tokyo_20260610_001.png
```

`VVV` 是當日同城市流水號。

## Server 環境變數與綁定

Cloudflare Worker 需要：

```text
OPENWEATHER_API_KEY=你的 OpenWeather API key
OPENAI_API_KEY=你的 OpenAI API key
OPENAI_IMAGE_MODEL=gpt-image-1
WALLPAPER_RETENTION_HOURS=24
PUBLIC_WORKER_ORIGIN=https://amigurumi-weather-theme-server.wemmei0130.workers.dev
```

R2 binding：

```text
WALLPAPER_BUCKET
```

手機端只需要填入 Worker URL，不需要保存 OpenWeather key。

## API

查天氣：

```text
https://your-worker.example.workers.dev?lat=22.6273&lon=120.3014&units=metric
```

查詢或建立桌布：

```text
https://your-worker.example.workers.dev?city=Kaohsiung&country=Taiwan&date=2026-06-10&weather=Rainy&period=Afternoon
```

回傳格式：

```json
{
  "file_name": "kaohsiung_20260610_001.png",
  "image_url": "https://your-worker.example.workers.dev/files/wallpapers%2Fkaohsiung%2Fkaohsiung_20260610_001.png",
  "scene_key": "kaohsiung|Taiwan|Rainy|Afternoon",
  "weather": "Rainy",
  "period": "Afternoon",
  "reused": false
}
```

## 使用方式

1. 安裝 APK。
2. 開啟 App。
3. 使用 GPS 自動定位，或勾選 `Use custom city instead of GPS` 並輸入城市。
4. 選擇語言設定：自動偵測系統預設，或勾選自定義語種。
5. 點選 `設定靜態桌布` 下載或建立 server 桌布並套用。
6. 點選 `開啟動態桌布` 套用動態桌布。
7. 點選 `更新 App` 從 GitHub Releases 檢查新版 APK。

## 重新生成規則

手機端會依設定間隔檢查狀態。只有下列任一項改變時，才會要求 server 使用新的 scene key：

- 地點
- 天氣
- 天色時段

溫度單獨改變不會重新建立新桌布。
