# 天氣桌布提示詞產生器（Windows）

這是獨立的 Windows WPF 工具，只負責根據天氣、時段、城市、節慶與畫風產生可交給 Gemini 或其他 AI agent 的桌布提示詞。它不會呼叫產圖 API，也不會讀取或保存任何 API key。

## 使用方式

1. 從天氣、時段與畫風下拉選單選擇條件。
2. 填寫城市；節慶可留空。
3. 複製產生的提示詞，貼到具產圖或網路查證能力的 AI agent。

提示詞會要求 agent 先用可靠資料查證城市景點與地標、排除錯誤項目，再把完整清單以有秩序的城市景觀納入圖片。若 agent 無法搜尋網路，應要求使用者提供地標清單，不得杜撰。

## 建置

```powershell
dotnet build .\src\WeatherWallpaperPromptGenerator.App\WeatherWallpaperPromptGenerator.App.csproj -c Release
dotnet run --project .\tests\WeatherWallpaperPromptGenerator.SmokeTests\WeatherWallpaperPromptGenerator.SmokeTests.csproj -c Release
dotnet run --project .\tests\WeatherWallpaperPromptGenerator.UiSmokeTests\WeatherWallpaperPromptGenerator.UiSmokeTests.csproj -c Release
dotnet publish .\src\WeatherWallpaperPromptGenerator.App\WeatherWallpaperPromptGenerator.App.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o .\dist
```

可執行檔為 `dist\WeatherWallpaperPromptGenerator.exe`。這是 win-x64 自含式單檔版本，不要求目標電腦預先安裝 .NET；`dist`、`bin` 與 `obj` 不納入 Git。

目前沒有商用程式碼簽章憑證，因此在其他電腦第一次啟動時，Windows 可能顯示未知發行者警告。正式對外發布前應使用可信憑證簽署 EXE。
