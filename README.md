# codex_AI_lab

## Amigurumi Weather Theme

Android wallpaper app for generating Amigurumi crochet city wallpapers from:

- GPS or custom city
- OpenWeather weather data
- Local date and time period rules
- Landmark and language rule tables
- OpenAI image generation when an API key is provided

## Current Build

- Package: `com.codex.amigurumiweather`
- Latest APK: `outputs/AmigurumiWeatherTheme-v1.2-debug.apk`
- Version: `1.2`
- Min SDK: 26
- Target SDK: 36

## Usage

1. Install the APK on Android.
2. Open the app.
3. Choose automatic GPS or enable custom city.
4. Set update interval in minutes. Default is `30`.
5. Enter OpenWeather API key for live weather.
6. Enter OpenAI API key only if AI image generation is needed.
7. Tap `Set static wallpaper` to generate and save the latest wallpaper.
8. Tap `Open animated Live Wallpaper` to use the latest generated image with dynamic weather overlays.

## Notes

The generated image intentionally avoids drawing clock, date, temperature, status bar, or lock-screen widgets. Those should come from the phone system UI, especially on Xiaomi/HyperOS lock screens.

## Auto Update Plan

Android apps cannot silently self-update from GitHub unless the device explicitly allows package installs and the user confirms installation. Future versions should implement one of these safe update paths:

- GitHub Releases checker: app checks the latest GitHub Release JSON, downloads a newer APK, then opens Android's package installer.
- Play Store / private distribution: preferred for signed production builds.
- In-app content updates: weather and generated wallpaper content can update automatically without reinstalling the app.

The app already supports automatic weather/content refresh for the Live Wallpaper based on the configured interval.
