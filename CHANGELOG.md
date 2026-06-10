# Changelog

## 2.3

- Live Wallpaper no longer remains on the sparse loading screen when the server image is unavailable or slow.
- When server download/generation is pending, the phone renders a complete local animated city wallpaper first and replaces it with the server AI image after download succeeds.
- Server wallpaper requests now prefer returning the latest same-city wallpaper immediately and refresh the exact weather/time scene in the background.

## 2.2

- Live Wallpaper no longer shows the old local default city artwork while waiting for a server wallpaper on fresh installs.
- When no server image is cached yet, Live Wallpaper shows a clean loading wallpaper with the city label and retries every 30 seconds.
- Added Cloudflare Cron tracking every 30 minutes for default cities Kaohsiung and Taipei.
- Other GPS/custom locations remain request-driven and generate when a phone asks for that location.

## 2.1

- Updated server-side AI prompt to place the city name in a pale, clean sky area.
- Prompt now explicitly avoids overlapping the city label with buildings, people, clouds, rain, or lock-screen widgets.
- Bumped server prompt version so existing same-scene images are regenerated with the new sky-label instruction.

## 2.0

- Live Wallpaper now always draws the city label as a phone-side overlay on top of server wallpaper backgrounds.
- This fixes generated dynamic wallpapers that missed the city name in the AI image.

## 1.9

- Simplified app UI so editable settings only show location mode/custom city and language mode/custom language.
- Hid theme server, weather backend, OpenAI key, model, and update interval fields behind defaults.
- Added app version text under the update button.
- Removed generated prompt text from the visible app screen.

## 1.8

- `Check app update` now compares the latest GitHub Release version with the installed app version.
- If the installed app is already up to date, the app shows an up-to-date message and does not download or open the APK installer.

## 1.7

- Phone storage now keeps only the latest dynamic wallpaper file.
- Successful wallpaper saves clean old wallpaper cache files to avoid excessive local storage use.
- Wallpaper writes now use a temporary file before replacing `last_wallpaper.png`.

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
