# Cloudflare Worker 部署說明

此 server 使用 Cloudflare Workers + R2。

## 會建立的資源

- Worker：`amigurumi-weather-theme-server`
- R2 bucket：`amigurumi-weather-wallpapers`
- R2 binding：`WALLPAPER_BUCKET`
- Worker vars：`OPENAI_IMAGE_MODEL=gpt-image-1`
- Worker secrets：
  - `OPENWEATHER_API_KEY`
  - `OPENAI_API_KEY`

## 本機命令

確認 Cloudflare 登入：

```powershell
npm.cmd run cf:whoami
```

建立 R2 bucket：

```powershell
npm.cmd run cf:create-bucket
```

設定 secrets：

```powershell
npx.cmd wrangler secret put OPENWEATHER_API_KEY
npx.cmd wrangler secret put OPENAI_API_KEY
```

部署 Worker：

```powershell
npm.cmd run cf:deploy
```

部署完成後，把 Worker URL 填到 Android App 的 `Theme server URL`。

## API 測試

查天氣：

```text
https://<worker-url>?lat=22.6273&lon=120.3014&units=metric
```

查詢或建立桌布：

```text
https://<worker-url>?city=Kaohsiung&country=Taiwan&date=2026-06-10&weather=Rainy&period=Afternoon
```
