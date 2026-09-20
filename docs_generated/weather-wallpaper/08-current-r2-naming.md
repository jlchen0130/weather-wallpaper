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
- `period`: `sunrise`, `morning`, `afternoon`, `sunset`, `night`, or `midnight`.
- `weather`: normalized value such as `sunny`, `cloudy`, `rainy`, `thunder`, or `typhoon`.
- Extension is always `.png`.

Example:

```text
wallpaper/knitted/cat/none_Kaohsiung_cat_sunrise_sunny.png
```

The Worker validates the upload token, PNG MIME type, PNG signature and 12 MiB size limit before writing to R2. Existing matching PNG files are reused without a daily-expiration requirement.
