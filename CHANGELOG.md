# Changelog

## Server

- Cloudflare Worker now keeps generated wallpapers and manifests for one day only.
- Expired R2 files are cleaned during API requests, and expired `/files/...` downloads return 404 after deletion.

## 1.6

- Offline mode now keeps the last downloaded dynamic wallpaper instead of generating a new fallback image.
- App shows a connection error message when the theme server or weather server cannot be reached.
- Live Wallpaper preserves the current background when server refresh fails.

## 1.5

- Added a server/mobile architecture for wallpaper generation.
- Added `Theme server URL` so the phone can request, download, and apply server-generated wallpapers.
- Added Cloudflare Worker theme server example with OpenWeather proxy, OpenAI image generation, R2 storage, scene manifests, and `city_YYYYMMDD_VVV.png` file naming.
- Live Wallpaper now tries the server wallpaper first, then falls back to phone-side generation.
- Added visible city name labeling in blank wallpaper space, using local Taiwan names and English names outside Taiwan.

## 1.4

- Added Samsung U23/S23-targeted APK asset naming.
- Added in-app update button that downloads the best APK from GitHub Releases based on phone model.
- Moved OpenWeather access behind a backend URL so the API key is not stored in the APK.
- Added Cloudflare Worker backend example.
- Added Traditional Chinese README instructions.

## 1.3

- Changed Live Wallpaper refresh semantics.
- The configured interval now checks scene state only.
- A new wallpaper is generated only when city/location, weather condition, or time period changes.
- Temperature-only changes no longer regenerate wallpaper.

## 1.2

- Removed generated clock/date/temperature text from wallpaper images.
- Left the upper wallpaper area clean for Xiaomi/Android lock-screen widgets.
- Fixed static wallpaper preview by showing a local preview immediately.
- Saved the latest generated wallpaper inside app storage.
- Live Wallpaper now uses the latest generated image as background and overlays dynamic weather effects.

## 1.1

- Added custom city mode.
- Added live update interval setting, defaulting to 30 minutes.
- Added animated Live Wallpaper service.
- Changed fallback city from Taipei to Kaohsiung.

## 1.0

- Added GPS/weather scene model.
- Added OpenWeather integration.
- Added OpenAI image generation integration.
- Added local fallback wallpaper renderer.
