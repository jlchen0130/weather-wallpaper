# Current R2 Naming Rule

All wallpaper assets are manually uploaded PNG files.

```text
wallpaper/<style>/<character>/<festival>_<city>_<character>_<period>_<weather>.png
```

Rules:

- `style`: `knitted` or `colored_pencil`.
- `character`: `person`, `cat`, `dog`, `hamster_chinchilla`, or `parrot`.
- `festival`: `none` or a normalized festival name.
- `city`: normalized city-level name such as `Kaohsiung`.
- `period`: `sunrise`, `morning`, `afternoon`, `sunset`, `night`, `midnight`, or `all_day`.
- `weather`: `sunny`, `partly_cloudy`, `cloudy`, `overcast`, `light_rain`, `heavy_rain`, `typhoon`, `fog`, `haze`, `strong_wind`, `thunder_shower`, `thunderstorm`, `heatwave`, or `cold_wave`.
- For `knitted/person`, only `sunny` and `partly_cloudy` use six time periods. All other weather uses `all_day` for both uploads and lookups, including festival assets.
- `torrential_rain` is an input alias for `heavy_rain`, not a stored category.
- `HsinchuCity`, `HsinchuCounty`, `ChiayiCity`, and `ChiayiCounty` are distinct city identifiers.
- Keep underscores in weather and `all_day`; do not parse filenames by fixed underscore positions.
- Extension is always `.png`.

Example:

```text
wallpaper/knitted/cat/none_Kaohsiung_cat_sunrise_sunny.png
```

The Worker validates the upload token, PNG MIME type, PNG signature and 12 MiB size limit before writing to R2. Existing matching PNG files are reused without a daily-expiration requirement.

Lookup prefers the current festival asset and falls back to the matching `none` asset when the festival asset is absent. Older non-knitted-person collections may also use their legacy `rainy`, `thunder`, and combined city/county keys; the qualified knitted-person collection never falls back to those obsolete combinations.
