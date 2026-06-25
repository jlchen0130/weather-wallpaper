# Current R2 Naming Rule

Admin manual uploads and server-generated wallpapers use the same Worker-owned naming rule.

```text
wallpaper/<style>/<char>/<festival>_<city>_<char>_<period>_<weather>.<ext>
```

Notes:

- `style`: `knitted` or `colored_pencil`.
- `char`: `person`, `cat`, `dog`, `hamster_chinchilla`, or `parrot`.
- `festival`: `none` when there is no festival.
- `city`: normalized city-level name, for example `Kaohsiung`.
- `period`: normalized period, for example `morning`, `afternoon`, `sunset`, `night`, or `midnight`.
- `weather`: normalized weather, for example `sunny`, `cloudy`, `rainy`, or `thunder`.
- `ext`: follows the actual uploaded/generated content type, such as `png`, `jpg`, `webp`, or `mp4`.

Examples:

```text
wallpaper/knitted/cat/none_Kaohsiung_cat_night_sunny.png
wallpaper/colored_pencil/person/christmas_Taipei_person_morning_cloudy.jpg
```

The admin APK sends metadata and the image file to `/admin/upload`; the Cloudflare Worker validates the upload token and decides the final R2 object key.
