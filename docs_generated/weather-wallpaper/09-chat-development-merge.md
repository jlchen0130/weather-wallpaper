# Development Decisions Merged Into This Project

更新日期：2026-09-20

## Final Operating Decisions

- Manual PNG generation and upload is the only wallpaper asset workflow.
- OpenAI Image API generation is permanently removed from Worker runtime code.
- Windows Admin is abandoned and is not part of this repository.
- Android Admin remains a development-only upload tool.
- Admin token is entered for the current session only, is not persisted, and must be revoked after development.
- The private GitHub repository stores source code and text documentation only. APK files are not committed.
- In-app updates from the private repository are removed. A separate public distribution area may be created only when an update is required.
- Android APK reproducibility is not a current project promise; the next major service will be rebuilt as a Cloudflare app server.

## Live Wallpaper Decision

The uploaded PNG is decoded as an Android `Bitmap` and drawn as the background by `DynamicWallpaperService`. The service continuously adds animated weather overlays. The PNG remains static; Android sees the running `WallpaperService` as the dynamic wallpaper.

## Six Periods

The canonical periods are `sunrise`, `morning`, `afternoon`, `sunset`, `night`, and `midnight`. Cron checks R2 coverage at six operating times. Existing matching PNG files are skipped; missing keys are logged and must be filled through the manual workflow.
