# Changelog

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
