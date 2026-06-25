# Changelog

## Server 2026-06-25

- Restored the admin manual upload endpoint at `/admin/upload`.
- Unified manual uploads and server-generated wallpapers under `wallpaper/<style>/<char>/<festival>_<city>_<char>_<period>_<weather>.<ext>`.
- Admin uploads now keep the uploaded file extension/content type and store metadata in R2 with `source=manual-chatgpt-upload`.

## Server 2026-06-21

- Fixed daily wallpaper refresh so an R2 object is reused only when its `generatedDate` matches the current Taipei date; stale objects are regenerated and overwritten under the same key.
- Updated the Worker `OPENAI_API_KEY` secret from the validated image-generator token source.
- Increased the OpenAI Image generation timeout from 55 seconds to 100 seconds and added sanitized generation failure logging.

## 4.35

- Fixed a mismatch where the app preview could show the latest cached wallpaper while the actual phone wallpaper still displayed an older image.
- Static wallpaper mode now applies the latest cached wallpaper when server or DNS lookup fails.
- Dynamic wallpaper mode now reloads the latest cached image on each refresh so the live wallpaper service does not keep an older in-memory background.

## 4.34

- Added an hourly background wallpaper sync receiver using AlarmManager.
- Background sync now refreshes static wallpapers even when the app UI is not open.
- Dynamic wallpaper mode now updates the shared wallpaper cache hourly instead of waiting only for the next time-period boundary.
- Wallpaper sync scheduling is restored after phone reboot.

## 4.33

- Fixed phone status handling for HTTP 304 server responses.
- The app now reads the Worker `x-wallpaper-status` header and shows whether the server is still generating, hit a daily limit, or had a temporary generation failure instead of incorrectly showing "server unavailable".

## 4.32

- Increased server wallpaper JSON request timeout from 30 seconds to 120 seconds so first-time OpenAI-generated wallpapers can complete instead of falling back to the previous cached wallpaper.
- Confirmed the missing Kaohsiung afternoon/person/knitted/cloudy wallpaper has now been generated and cached on R2.

## 4.31

- Updated the launcher app icon to a cute Q-version weather symbol with a cloud, sun, face, and raindrops.

## 4.30

- Simplified the phone home screen to show only the latest wallpaper preview and sync status.
- Moved location mode, custom city, character, style, dynamic wallpaper preference, and app update into the settings screen.
- Added automatic wallpaper sync on app launch and hourly checks after launch.
- Removed the manual dynamic wallpaper apply flow from the home screen; dynamic mode now updates through the cached live wallpaper source.
- Added server-weather request signaling so the Worker can use OpenWeather from the server side for newer clients.

## 4.20

- Fixed app update version parsing. Older 4.1 builds parsed `v4.2` as `402`, so this release uses `v4.20` while keeping Android `versionCode=420`.
- Future version parsing now maps `v4.3` to `430`, `v4.20` to `420`, and supports patch components.

## 4.2

- Hardened server failure handling for phone clients.
- Android now treats server HTTP 304 as "keep the current wallpaper" instead of a generic connection failure.
- Live Wallpaper no longer marks a scene as synced unless a new server image was actually downloaded.
- Added Worker generation locks, daily generation limits, guarded Telegram alerts, and safer R2 file serving.

## Server 3.9 compatibility rebuild

- Replaced the Cloudflare Worker with a defensive three-stage compatibility architecture.
- Added legacy and new query parsing for `loc/city`, `char/character`, `weather`, `period`, and `style`.
- Added city-level Taiwan location normalization, four-code weather convergence, festival detection, and strict R2 keys in `wallpaper/<style>/<festival>_<char>_<loc>_<period>_<weather>.mp4`.
- Added R2-first cache handling to avoid OpenAI cost on cache hits.
- Added OpenAI failure fallback returning HTTP 304 so clients keep the current wallpaper, plus Telegram alerting via Worker environment secrets.
- Added R2 generation locks, daily city/style generation limits, guarded Telegram waitUntil handling, OpenAI/Telegram timeouts, and `/files` prefix restrictions.
- Updated Android client handling so HTTP 304 means "keep current wallpaper" and does not mark a scene as synced when no new server image was downloaded.
- Rewrote the Cloudflare deployment runbook with current secrets, SRE behavior, cron status, smoke tests, rollback notes, and admin upload status.

## 4.1

- Added a phone-side wallpaper style selector with Knitted and Colored Pencil options.
- Sent the selected style to the Cloudflare Worker and included it in scene keys so style changes sync separate wallpapers.
- Added style metadata, R2 object grouping, manifest paths, file names, admin upload fields, and prompt switching on the Worker.
- Deployed the Worker with the style-aware generation and lookup rules.

## 3.2

- Server AI prompts now use only 2-3 local landmark anchors per generated wallpaper.
- Server prompts now ask for Amigurumi people doing daily life actions such as commuting, shopping, chatting, taking photos, relaxing, and browsing night markets.
- Server daily pre-generation now prepares five city wallpapers per day: Morning, Noon, Sunset, Evening, and DeepNight.
- Server wallpaper scene keys now include the date so each day can receive fresh generated wallpapers.
- Phone-side time period rules now match the five daily generation periods.

## 3.1

- Enforced the wallpaper generation policy: new AI wallpapers may only be generated by the Cloudflare Worker through OpenAI Image and stored in R2.
- Removed phone-side OpenAI Image generation code and hidden OpenAI key/model settings from the APK.
- Removed the bundled AI-generated Kaohsiung wallpaper asset so the phone does not use non-R2 AI image sources.

## 3.0

- Bundled the latest Kaohsiung landmark wallpaper directly into the APK.
- If the server still returns the older Kaohsiung cached image, the phone now uses the bundled latest Kaohsiung wallpaper instead.
- Kaohsiung static and dynamic wallpaper flows can sync the latest image even before Cloudflare R2 is refreshed.

## 2.9

- Made Live Wallpaper motion visibly animated instead of relying on very subtle weather overlays.
- Added drifting clouds, yarn-like light particles, evening light flicker, sunny glow, and snow motion overlays.
- AI-generated backgrounds remain detailed static art while the Live Wallpaper layer supplies continuous motion.

## 2.8

- Live Wallpaper now checks the theme server on every refresh interval even when city, weather, and time period are unchanged.
- This lets phones automatically pick up a newer server wallpaper file for the same scene.
- Static wallpaper mode remains unchanged and is not auto-switched to Live Wallpaper.

## 2.7

- Expanded Kaohsiung landmark data for AI wallpaper prompts.
- Kaohsiung scenes now include a broader city-level landmark set such as Lotus Pond, Dragon and Tiger Pagodas, Fo Guang Shan Buddha Museum, Kaohsiung Music Center, Cijin Lighthouse, Dome of Light, Sizihwan, Central Park, and Liuhe Night Market.

## 2.6

- Added phone-side wallpaper mode tracking for static versus dynamic wallpaper use.
- Dynamic wallpaper auto-refresh now updates the Live Wallpaper only when the app's Live Wallpaper service is active.
- Static wallpaper users keep their existing static wallpaper mode; cached downloads do not force-switch them to dynamic wallpaper.

## Server

- Added `force=1` / `refresh=1` support to bypass same-scene wallpaper cache and generate a new server wallpaper on demand.
- Bumped the server prompt version to city-level v3 so new AI images use county/city-level geography instead of district-level details.

## 2.5

- GPS reverse geocoding now uses Taiwan county/city level instead of district/township level.
- Added Traditional Chinese and English mappings for major Taiwan cities so AI generation uses city-level prompts such as Kaohsiung.
- Added landmark data for New Taipei, Taoyuan, Taichung, and Tainan.

## 2.4

- Fixed weather backend parsing when the server returns simplified weather strings such as `Cloudy`.
- App now supports both the server proxy format and the original OpenWeather `weather[]` array format.

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
