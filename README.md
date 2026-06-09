# codex_AI_lab

## Amigurumi Weather Theme

Amigurumi Weather Theme 是一個 Android 桌布 App，會依照手機位置、自訂城市、天氣 API、日期時間與城市地標資料，產生鉤針編織風格的城市桌布，並可套用成靜態桌布或動態 Live Wallpaper。

## 目前版本

- App package: `com.codex.amigurumiweather`
- Version: `1.4`
- Min SDK: 26
- Target SDK: 36
- 通用 APK: `outputs/AmigurumiWeatherTheme-v1.4-universal-debug.apk`
- Samsung U23/S23 APK: `outputs/AmigurumiWeatherTheme-v1.4-samsung-u23-debug.apk`

## 主要功能

- 可使用 GPS 自動判斷城市，也可手動指定城市，例如 `Kaohsiung`。
- 天氣資料由後端代理 API 提供，OpenWeather API key 不放在 APK 內。
- 支援 OpenAI Image API 產生 Amigurumi 鉤針城市桌布。
- Live Wallpaper 會使用最新生成圖片作為背景，再疊加動態天氣效果。
- 檢查間隔可手動設定，預設 `30` 分鐘。
- 只有地點、天氣、天色時段其中之一改變時才會重新生成桌布；單純溫度改變不會重新生成。
- App 內有 `Check app update` 更新按鍵，會從 GitHub Releases 下載新版 APK。
- 下載更新前會依手機型號挑選 APK；Samsung U23/S23 會優先下載 Samsung 專用檔名版本，其他手機使用通用版。

## 使用方式

1. 安裝 APK。
2. 開啟 App。
3. 選擇 GPS 自動定位，或勾選 `Use custom city instead of GPS` 並輸入城市。
4. 設定 `Live update interval minutes`，例如 `30`。
5. 輸入 `Weather backend URL`。
6. 如需 AI 生成圖片，輸入 OpenAI API key。
7. 點選 `Set static wallpaper` 產生並設定靜態桌布。
8. 點選 `Open animated Live Wallpaper` 開啟動態桌布設定。
9. 點選 `Check app update` 從 GitHub Releases 檢查並下載新版。

## 手機權限

- 位置權限：GPS 自動定位需要。
- 網路權限：查詢天氣、呼叫圖片生成、檢查 GitHub 更新需要。
- 設定桌布權限：將圖片套用為桌布需要。
- 安裝未知來源 App：App 下載新版 APK 後，Android 仍會要求使用者確認安裝。

Android 不允許一般 App 靜默自行安裝 APK，所以即使使用 App 內更新按鍵，仍需在系統安裝畫面手動確認。

## 天氣後端

OpenWeather API key 不應放在 Android APK。此版本改成呼叫後端 URL，由後端持有 OpenWeather key。

Cloudflare Worker 範例檔案：

```text
backend/cloudflare-worker-openweather.js
```

Worker Secret：

```text
OPENWEATHER_API_KEY=你的 OpenWeather API key
```

App 呼叫格式：

```text
https://your-worker.example.workers.dev?lat=22.6273&lon=120.3014&units=metric
```

後端會回傳精簡天氣 JSON：

```json
{
  "weather": "Rainy",
  "temp_min": 26,
  "temp_max": 30,
  "city": "Kaohsiung",
  "country": "Taiwan"
}
```

## 鎖定畫面資訊

生成圖片會避免繪製手機時間、日期、溫度、狀態列或鎖定畫面 widget。這些資訊應由手機系統 UI 提供，避免和小米、三星等系統內建資訊重疊。
