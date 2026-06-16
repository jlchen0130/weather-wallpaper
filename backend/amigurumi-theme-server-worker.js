const WEATHER_MAP = {
  Clear: "晴",
  Clouds: "多云",
  Rain: "中雨",
  Drizzle: "小雨",
  Thunderstorm: "雷阵雨",
  Snow: "中雪",
  Mist: "雾",
  Fog: "雾",
  Haze: "霾",
  Smoke: "霾",
  Dust: "浮尘",
  Sand: "扬沙"
};
const PROMPT_VERSION = "style-select-festival-weather-v8";
const STYLE_ALIASES = {
  knitted: "knitted",
  knit: "knitted",
  crochet: "knitted",
  amigurumi: "knitted",
  colored_pencil: "colored_pencil",
  color_pencil: "colored_pencil",
  pencil: "colored_pencil",
  pastel_pencil: "colored_pencil"
};
const DAILY_PERIODS = ["Morning", "Afternoon", "Sunset", "Night", "Midnight", "sunraise"];
const SUPPORTED_WEATHERS = [
  "晴", "多云", "阴", "阵雨", "雷阵雨", "雷阵雨伴有冰雹", "雨夹雪", "小雨", "中雨", "大雨", "暴雨", "大暴雨", "特大暴雨",
  "阵雪", "小雪", "中雪", "大雪", "暴雪", "雾", "冻雨", "沙尘暴", "小雨-中雨", "中雨-大雨", "大雨-暴雨",
  "暴雨-大暴雨", "大暴雨-特大暴雨", "小雪-中雪", "中雪-大雪", "大雪-暴雪", "浮尘", "扬沙", "强沙尘暴", "霾",
  "Sunny", "Cloudy", "Rainy", "Snowy", "Foggy"
];
const WEATHER_ALIASES = {
  Sunny: "晴",
  Clear: "晴",
  Cloudy: "多云",
  Clouds: "多云",
  Rainy: "中雨",
  Rain: "中雨",
  Drizzle: "小雨",
  Thunderstorm: "雷阵雨",
  Snowy: "中雪",
  Snow: "中雪",
  Foggy: "雾",
  Fog: "雾",
  Mist: "雾",
  Haze: "霾"
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return cors();
    if (url.pathname === "/admin/upload") return uploadPage(request, env);
    if (url.pathname.startsWith("/files/")) return serveFile(url, env);
    if (url.searchParams.has("lat") && url.searchParams.has("lon") && !url.searchParams.has("city")) {
      return weather(request, env);
    }
    if (url.searchParams.has("city")) return wallpaper(request, env, ctx);
    return json({
      service: "amigurumi-theme-server",
      routes: [
        "/?lat=22.6273&lon=120.3014&units=metric",
        "/?city=Kaohsiung&country=Taiwan&date=2026-06-10&weather=Rainy&period=Afternoon",
        "/admin/upload"
      ]
    });
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(refreshTrackedCities(env));
  }
};

async function uploadPage(request, env) {
  if (!env.WALLPAPER_BUCKET) return json({ error: "WALLPAPER_BUCKET R2 binding is not configured" }, 500);
  if (!env.MANUAL_UPLOAD_TOKEN) return json({ error: "MANUAL_UPLOAD_TOKEN is not configured" }, 500);
  const url = new URL(request.url);
  if (request.method === "GET") return uploadForm();
  if (request.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const form = await request.formData();
  if (!authorized(request, url, env, stringValue(form.get("token"), ""))) return json({ error: "Unauthorized" }, 401);
  const image = form.get("image");
  if (!image || typeof image === "string" || !image.arrayBuffer) {
    return json({ error: "Missing image file" }, 400);
  }
  const contentType = image.type || "application/octet-stream";
  if (!["image/png", "image/jpeg", "image/webp"].includes(contentType)) {
    return json({ error: "Only PNG, JPEG, or WebP images are supported" }, 400);
  }

  const scene = {
    city: stringValue(form.get("city"), "Kaohsiung"),
    cityLocal: stringValue(form.get("cityLocal"), stringValue(form.get("city"), "Kaohsiung")),
    country: stringValue(form.get("country"), "Taiwan"),
    date: stringValue(form.get("date"), new Date().toISOString().slice(0, 10)),
    weather: normalizeWeather(stringValue(form.get("weather"), "Cloudy")),
    period: normalizePeriod(stringValue(form.get("period"), "Afternoon")),
    character: normalizeCharacter(stringValue(form.get("character"), "person")),
    style: normalizeStyle(stringValue(form.get("style"), "knitted")),
    festival: normalizeFestival(stringValue(form.get("festival"), "")),
    tempMin: stringValue(form.get("tempMin"), "27"),
    tempMax: stringValue(form.get("tempMax"), "32"),
    landmarks: stringValue(form.get("landmarks"), "manual upload")
      .split("|")
      .map((item) => item.trim())
      .filter(Boolean)
  };

  const result = await storeUploadedWallpaper(env, url, scene, image, contentType);
  if ((request.headers.get("accept") || "").includes("text/html")) {
    return html(`<!doctype html><meta charset="utf-8"><title>Uploaded</title><body style="font-family:sans-serif;padding:24px"><h1>Uploaded</h1><p>${escapeHtml(result.file_name)}</p><p><a href="${result.image_url}">Open image</a></p><p><a href="/admin/upload">Upload another</a></p></body>`);
  }
  return json(result);
}

function uploadForm() {
  const weatherOptions = SUPPORTED_WEATHERS.slice(0, 33)
    .map((item) => `<option${item === "多云" ? " selected" : ""}>${escapeHtml(item)}</option>`)
    .join("");
  return html(`<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Manual Wallpaper Upload</title>
<body style="font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:720px;margin:32px auto;padding:0 18px;line-height:1.5">
<h1>手動上傳桌布</h1>
<form method="post" enctype="multipart/form-data">
  <p><label>Upload token<br><input name="token" type="password" required style="width:100%;padding:10px"></label></p>
  <p><label>Image<br><input name="image" type="file" accept="image/png,image/jpeg,image/webp" required></label></p>
  <p><label>City<br><input name="city" value="Kaohsiung" required style="width:100%;padding:10px"></label></p>
  <p><label>City local<br><input name="cityLocal" value="Kaohsiung" style="width:100%;padding:10px"></label></p>
  <p><label>Country<br><input name="country" value="Taiwan" style="width:100%;padding:10px"></label></p>
  <p><label>Date<br><input name="date" type="date" style="width:100%;padding:10px"></label></p>
  <p><label>Festival, blank for none<br><input name="festival" placeholder="小暑" style="width:100%;padding:10px"></label></p>
  <p><label>Weather<br><select name="weather" style="width:100%;padding:10px">${weatherOptions}</select></label></p>
  <p><label>Period<br><select name="period" style="width:100%;padding:10px"><option>sunraise</option><option>Morning</option><option selected>Afternoon</option><option>Sunset</option><option>Night</option><option>Midnight</option></select></label></p>
  <p><label>Character<br><select name="character" style="width:100%;padding:10px"><option value="person">人</option><option value="cat">貓</option><option value="dog">狗</option><option value="hamster_chinchilla">倉鼠/龍貓</option></select></label></p>
  <p><label>Style<br><select name="style" style="width:100%;padding:10px"><option value="knitted">針織</option><option value="colored_pencil">色鉛筆</option></select></label></p>
  <p><label>Temperature min<br><input name="tempMin" value="27" inputmode="numeric" style="width:100%;padding:10px"></label></p>
  <p><label>Temperature max<br><input name="tempMax" value="32" inputmode="numeric" style="width:100%;padding:10px"></label></p>
  <p><label>Landmarks, separated by |<br><input name="landmarks" value="85 Sky Tower|Love River|Pier-2 Art Center" style="width:100%;padding:10px"></label></p>
  <p><button style="padding:12px 18px">Upload to R2</button></p>
</form>
</body>
</html>`);
}

async function storeUploadedWallpaper(env, url, scene, image, contentType) {
  const citySlug = slug(scene.city);
  const extension = extensionFor(contentType);
  const fileName = wallpaperFileName(scene, extension);
  const objectKey = wallpaperObjectKey(scene, fileName);
  const sceneKey = [citySlug, scene.country, scene.date, scene.weather, scene.period, scene.character, scene.style, scene.festival || "", "manual-upload"].join("|");
  const bytes = await image.arrayBuffer();
  await env.WALLPAPER_BUCKET.put(objectKey, bytes, {
    httpMetadata: { contentType },
    customMetadata: {
      city: scene.city,
      country: scene.country,
      weather: scene.weather,
      period: scene.period,
      character: scene.character,
      style: scene.style,
      festival: scene.festival || "",
      date: scene.date,
      sceneKey,
      source: "manual-upload"
    }
  });

  const manifest = {
    file_name: fileName,
    object_key: objectKey,
    city: scene.city,
    country: scene.country,
    weather: scene.weather,
    period: scene.period,
    character: scene.character,
    style: scene.style,
    festival: scene.festival || "",
    date: scene.date,
    scene_key: sceneKey,
    source: "manual-upload",
    animation: {
      type: "android-live-wallpaper-overlay",
      weather: scene.weather,
      period: scene.period
    }
  };
  const manifestKey = manifestObjectKey(scene, citySlug, "manual-" + hash(sceneKey + "|" + fileName));
  await env.WALLPAPER_BUCKET.put(manifestKey, JSON.stringify(manifest), {
    httpMetadata: { contentType: "application/json; charset=utf-8" }
  });
  return {
    ...manifest,
    image_url: fileUrl(url, objectKey),
    reused: false,
    expires_at: null
  };
}

async function weather(request, env) {
  const url = new URL(request.url);
  const lat = url.searchParams.get("lat");
  const lon = url.searchParams.get("lon");
  const units = url.searchParams.get("units") || "metric";
  if (!env.OPENWEATHER_API_KEY) return json({ error: "OPENWEATHER_API_KEY is not configured" }, 500);

  const api = new URL("https://api.openweathermap.org/data/2.5/weather");
  api.searchParams.set("lat", lat);
  api.searchParams.set("lon", lon);
  api.searchParams.set("units", units);
  api.searchParams.set("appid", env.OPENWEATHER_API_KEY);

  const response = await fetch(api);
  const body = await response.json();
  if (!response.ok) return json({ error: body.message || "OpenWeather error" }, response.status);
  const main = body.weather?.[0]?.main || "Clouds";
  return json({
    weather: WEATHER_MAP[main] || main,
    temp_min: body.main?.temp_min ?? 27,
    temp_max: body.main?.temp_max ?? 32,
    city: body.name || "",
    country: body.sys?.country || ""
  });
}

async function wallpaper(request, env, ctx) {
  if (!env.WALLPAPER_BUCKET) return json({ error: "WALLPAPER_BUCKET R2 binding is not configured" }, 500);
  if (!env.OPENAI_API_KEY) return json({ error: "OPENAI_API_KEY is not configured" }, 500);

  const url = new URL(request.url);
  const scene = readScene(url);
  const force = url.searchParams.get("force") === "1" || url.searchParams.get("refresh") === "1";
  if (force && !authorized(request, url, env)) {
    return json({ error: "force refresh requires admin authorization" }, 401);
  }
  const result = await ensureWallpaper(env, url, scene, { allowLatest: !force, force, ctx });
  return json(result);
}

async function ensureWallpaper(env, url, scene, options = {}) {
  const citySlug = slug(scene.city);
  const sceneKey = [citySlug, scene.country, scene.date, scene.weather, scene.period, scene.character, scene.style, scene.festival || "", PROMPT_VERSION].join("|");
  const manifestKey = manifestObjectKey(scene, citySlug, hash(sceneKey));
  const existing = options.force ? null : await env.WALLPAPER_BUCKET.get(manifestKey);
  if (existing) {
    const manifest = await existing.json();
    const existingImage = await env.WALLPAPER_BUCKET.get(manifest.object_key);
    if (!existingImage) {
      await env.WALLPAPER_BUCKET.delete(manifestKey);
    } else {
      return {
        ...manifest,
        image_url: fileUrl(url, manifest.object_key),
        reused: true,
        expires_at: null
      };
    }
  }

  if (options.allowLatest) {
    const latest = await latestCityWallpaper(env, url, citySlug, scene.character, scene.style);
    if (latest) {
      return {
        ...latest,
        scene_key: sceneKey,
        requested_weather: scene.weather,
        requested_period: scene.period,
        reused: true,
        pending_refresh: false,
        limited_reason: "client requests reuse latest wallpaper; scheduled jobs create new scenes"
      };
    }
    const anyCharacterLatest = await latestCityWallpaper(env, url, citySlug, null, scene.style);
    if (anyCharacterLatest) {
      return {
        ...anyCharacterLatest,
        scene_key: sceneKey,
        requested_weather: scene.weather,
        requested_period: scene.period,
        requested_character: scene.character,
        reused: true,
        pending_refresh: false,
        limited_reason: "requested character wallpaper not found; reused latest city wallpaper"
      };
    }
    const globalLatest = await latestWallpaper(env, url, scene.style);
    if (globalLatest) {
      return {
        ...globalLatest,
        scene_key: sceneKey,
        requested_city: scene.city,
        requested_weather: scene.weather,
        requested_period: scene.period,
        requested_character: scene.character,
        reused: true,
        pending_refresh: false,
        limited_reason: "requested city wallpaper not found; reused latest available wallpaper"
      };
    }
    return {
      error: "no wallpaper available for this city yet",
      scene_key: sceneKey,
      requested_weather: scene.weather,
      requested_period: scene.period,
      requested_character: scene.character,
      reused: false,
      pending_refresh: false
    };
  }

  return createWallpaperIfAllowed(env, url, scene, citySlug, sceneKey, manifestKey);
}

async function createWallpaperIfAllowed(env, url, scene, citySlug, sceneKey, manifestKey) {
  const latest = await latestCityWallpaper(env, url, citySlug, scene.character, scene.style);
  const lockKey = `locks/${citySlug}/${hash(sceneKey)}.lock`;
  const lock = await env.WALLPAPER_BUCKET.get(lockKey);
  if (lock && !isLockExpired(lock.uploaded)) {
    if (latest) {
      return {
        ...latest,
        scene_key: sceneKey,
        requested_weather: scene.weather,
        requested_period: scene.period,
        reused: true,
        pending_refresh: true,
        limited_reason: "generation already pending"
      };
    }
    return {
      error: "generation already pending",
      scene_key: sceneKey,
      requested_weather: scene.weather,
      requested_period: scene.period,
      reused: false,
      pending_refresh: true
    };
  }

  const dailyLimit = maxDailyGenerationsPerCity(env);
  const dailyCount = await countDailyWallpapers(env, citySlug, scene.date);
  if (dailyCount >= dailyLimit) {
    if (latest) {
      return {
        ...latest,
        scene_key: sceneKey,
        requested_weather: scene.weather,
        requested_period: scene.period,
        reused: true,
        pending_refresh: false,
        limited_reason: `daily generation limit reached: ${dailyLimit}`
      };
    }
    return {
      error: `daily generation limit reached: ${dailyLimit}`,
      scene_key: sceneKey,
      requested_weather: scene.weather,
      requested_period: scene.period,
      reused: false,
      pending_refresh: false,
      limited_reason: `daily generation limit reached: ${dailyLimit}`
    };
  }

  await env.WALLPAPER_BUCKET.put(lockKey, JSON.stringify({
    scene_key: sceneKey,
    created_at: new Date().toISOString()
  }), {
    httpMetadata: { contentType: "application/json; charset=utf-8" }
  });
  try {
    return await createWallpaper(env, url, scene, citySlug, sceneKey, manifestKey);
  } finally {
    await env.WALLPAPER_BUCKET.delete(lockKey);
  }
}

async function createWallpaper(env, url, scene, citySlug, sceneKey, manifestKey) {
  const fileName = wallpaperFileName(scene, ".png");
  const objectKey = wallpaperObjectKey(scene, fileName);
  const prompt = buildPrompt(scene);
  const imageBytes = await generateImage(env, prompt);
  await env.WALLPAPER_BUCKET.put(objectKey, imageBytes, {
    httpMetadata: { contentType: "image/png" },
    customMetadata: {
      city: scene.city,
      country: scene.country,
      weather: scene.weather,
      period: scene.period,
      character: scene.character,
      style: scene.style,
      festival: scene.festival || "",
      date: scene.date,
      sceneKey
    }
  });

  const manifest = {
    file_name: fileName,
    object_key: objectKey,
    city: scene.city,
    country: scene.country,
    weather: scene.weather,
    period: scene.period,
    character: scene.character,
    style: scene.style,
    festival: scene.festival || "",
    date: scene.date,
    scene_key: sceneKey,
    animation: {
      type: "android-live-wallpaper-overlay",
      weather: scene.weather,
      period: scene.period
    }
  };
  await env.WALLPAPER_BUCKET.put(manifestKey, JSON.stringify(manifest), {
    httpMetadata: { contentType: "application/json; charset=utf-8" }
  });

  return {
    ...manifest,
    image_url: fileUrl(url, objectKey),
    reused: false,
    expires_at: null
  };
}

async function latestCityWallpaper(env, url, citySlug, character, style) {
  const listed = await env.WALLPAPER_BUCKET.list({
    prefix: character ? `wallpapers/${characterFolder(character)}/` : "wallpapers/",
    limit: 1000
  });
  const objects = (listed.objects || [])
    .filter((object) => {
      const metadata = object.customMetadata || {};
      return slug(metadata.city || "") === citySlug
        && (!style || normalizeStyle(metadata.style || "knitted") === normalizeStyle(style));
    })
    .sort((a, b) => new Date(b.uploaded).getTime() - new Date(a.uploaded).getTime());
  if (!objects.length) return null;
  const object = objects[0];
  const metadata = object.customMetadata || {};
  const fileName = object.key.split("/").pop() || object.key;
  return {
    file_name: fileName,
    object_key: object.key,
    city: metadata.city || citySlug,
    country: metadata.country || "",
    weather: metadata.weather || "",
    period: metadata.period || "",
    character: metadata.character || "person",
    style: normalizeStyle(metadata.style || "knitted"),
    festival: metadata.festival || "",
    date: metadata.date || "",
    image_url: fileUrl(url, object.key),
    expires_at: null
  };
}

async function latestWallpaper(env, url, style) {
  const listed = await env.WALLPAPER_BUCKET.list({
    prefix: "wallpapers/",
    limit: 1000
  });
  const objects = (listed.objects || [])
    .filter((object) => {
      const metadata = object.customMetadata || {};
      return !style || normalizeStyle(metadata.style || "knitted") === normalizeStyle(style);
    })
    .sort((a, b) => new Date(b.uploaded).getTime() - new Date(a.uploaded).getTime());
  if (!objects.length) return null;
  const object = objects[0];
  const metadata = object.customMetadata || {};
  const fileName = object.key.split("/").pop() || object.key;
  return {
    file_name: fileName,
    object_key: object.key,
    city: metadata.city || "",
    country: metadata.country || "",
    weather: metadata.weather || "",
    period: metadata.period || "",
    character: metadata.character || "person",
    style: normalizeStyle(metadata.style || "knitted"),
    festival: metadata.festival || "",
    date: metadata.date || "",
    image_url: fileUrl(url, object.key),
    expires_at: null
  };
}

async function refreshTrackedCities(env) {
  if (!env.OPENWEATHER_API_KEY || !env.OPENAI_API_KEY || !env.WALLPAPER_BUCKET) return;
  const cities = trackedCities(env);
  const origin = env.PUBLIC_WORKER_ORIGIN || "https://amigurumi-weather-theme-server.wemmei0130.workers.dev";
  const url = new URL(origin);
  for (const city of cities) {
    try {
      const weatherInfo = await fetchWeatherByLocation(env, city.lat, city.lon);
      const scene = {
        city: city.city,
        cityLocal: city.cityLocal || city.city,
        country: city.country || "Taiwan",
        date: todayForOffset(city.utcOffset || 8),
        weather: weatherInfo.weather,
        period: timePeriodForOffset(city.utcOffset || 8),
        character: "person",
        style: "knitted",
        tempMin: String(Math.round(weatherInfo.temp_min)),
        tempMax: String(Math.round(weatherInfo.temp_max)),
        landmarks: city.landmarks || ["central station", "old town market", "city park"]
      };
      scene.festival = festivalFor(scene.country, scene.date);
      await ensureWallpaper(env, url, scene);
    } catch (error) {
      console.log(`tracked city refresh failed: ${city.city}: ${error.message}`);
    }
  }
}

async function fetchWeatherByLocation(env, lat, lon) {
  const api = new URL("https://api.openweathermap.org/data/2.5/weather");
  api.searchParams.set("lat", lat);
  api.searchParams.set("lon", lon);
  api.searchParams.set("units", "metric");
  api.searchParams.set("appid", env.OPENWEATHER_API_KEY);
  const response = await fetch(api);
  const body = await response.json();
  if (!response.ok) throw new Error(body.message || "OpenWeather error");
  const main = body.weather?.[0]?.main || "Clouds";
  return {
    weather: WEATHER_MAP[main] || main,
    temp_min: body.main?.temp_min ?? 27,
    temp_max: body.main?.temp_max ?? 32
  };
}

function trackedCities(env) {
  if (env.TRACKED_CITIES) {
    try {
      return JSON.parse(env.TRACKED_CITIES);
    } catch (error) {
      console.log(`invalid TRACKED_CITIES: ${error.message}`);
    }
  }
  return [
    {
      city: "Kaohsiung",
      cityLocal: "Kaohsiung",
      country: "Taiwan",
      lat: 22.6273,
      lon: 120.3014,
      utcOffset: 8,
      landmarks: [
        "85 Sky Tower",
        "Love River",
        "Pier-2 Art Center",
        "Lotus Pond",
        "Dragon and Tiger Pagodas",
        "Fo Guang Shan Buddha Museum",
        "Kaohsiung Music Center",
        "Cijin Lighthouse",
        "Dome of Light",
        "Sizihwan",
        "Central Park",
        "Liuhe Night Market"
      ]
    },
    {
      city: "Taipei",
      cityLocal: "Taipei",
      country: "Taiwan",
      lat: 25.0330,
      lon: 121.5654,
      utcOffset: 8,
      landmarks: ["Taipei 101", "Ximending", "Raohe Night Market"]
    }
  ];
}

function todayForOffset(offset) {
  return shiftedDate(offset).toISOString().slice(0, 10);
}

function timePeriodForOffset(offset) {
  const hour = shiftedDate(offset).getUTCHours();
  if (hour >= 5 && hour <= 6) return "sunraise";
  if (hour >= 7 && hour <= 11) return "Morning";
  if (hour >= 12 && hour <= 16) return "Afternoon";
  if (hour >= 17 && hour <= 18) return "Sunset";
  if (hour >= 19 && hour <= 23) return "Night";
  return "Midnight";
}

function shiftedDate(offset) {
  return new Date(Date.now() + offset * 60 * 60 * 1000);
}

async function serveFile(url, env) {
  if (!env.WALLPAPER_BUCKET) return json({ error: "WALLPAPER_BUCKET R2 binding is not configured" }, 500);
  const key = decodeURIComponent(url.pathname.replace(/^\/files\//, ""));
  const object = await env.WALLPAPER_BUCKET.get(key);
  if (!object) return json({ error: "File not found" }, 404);
  return new Response(object.body, {
    headers: {
      "content-type": object.httpMetadata?.contentType || "application/octet-stream",
      "cache-control": "public, max-age=86400",
      "access-control-allow-origin": "*"
    }
  });
}

function isLockExpired(uploaded) {
  if (!uploaded) return false;
  return Date.now() - new Date(uploaded).getTime() > 15 * 60 * 1000;
}

function maxDailyGenerationsPerCity(env) {
  const value = Number(env.MAX_DAILY_GENERATIONS_PER_CITY || 5);
  return Math.max(1, Math.min(20, value));
}

async function countDailyWallpapers(env, citySlug, date) {
  let count = 0;
  let cursor;
  do {
    const listed = await env.WALLPAPER_BUCKET.list({ prefix: "wallpapers/", cursor, limit: 1000 });
    count += (listed.objects || []).filter((object) => {
      const metadata = object.customMetadata || {};
      return slug(metadata.city || "") === citySlug && metadata.date === date;
    }).length;
    cursor = listed.truncated ? listed.cursor : undefined;
  } while (cursor);
  return count;
}

function readScene(url) {
  const landmarks = (url.searchParams.get("landmarks") || "")
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);
  const scene = {
    city: url.searchParams.get("city") || "Kaohsiung",
    cityLocal: url.searchParams.get("cityLocal") || url.searchParams.get("city") || "Kaohsiung",
    country: url.searchParams.get("country") || "Taiwan",
    date: url.searchParams.get("date") || new Date().toISOString().slice(0, 10),
    weather: normalizeWeather(url.searchParams.get("weather") || "Cloudy"),
    period: normalizePeriod(url.searchParams.get("period") || "Afternoon"),
    character: normalizeCharacter(url.searchParams.get("character") || "person"),
    style: normalizeStyle(url.searchParams.get("style") || "knitted"),
    tempMin: url.searchParams.get("tempMin") || "27",
    tempMax: url.searchParams.get("tempMax") || "32",
    landmarks: landmarks.length ? landmarks : ["central station", "old town market", "city park"]
  };
  scene.festival = normalizeFestival(url.searchParams.get("festival") || festivalFor(scene.country, scene.date));
  return scene;
}

function buildPrompt(scene) {
  const isTaiwan = scene.country === "Taiwan";
  const landmarks = selectedLandmarks(scene.landmarks);
  const character = characterPrompt(scene.character);
  const style = stylePrompt(scene.style);
  const festival = normalizeFestival(scene.festival);
  const weatherText = weatherPrompt(scene.weather);
  const timeText = timePrompt(scene.period);
  return [
    "手機動態桌布插畫，直式 9:16，高解析度，溫暖可愛的童話氛圍。",
    style,
    "The composition should feel like a natural miniature fairy-tale city landscape, not a collage.",
    "Use a distant wide-angle establishing view from a slightly elevated viewpoint, so landmarks are distributed naturally across the city scene with open sky and readable depth.",
    "Use only city or county-level geography. Do not depict districts, townships, streets, neighborhoods, or overly specific local areas.",
    `City: ${scene.city}. Country: ${scene.country}.`,
    `Weather: ${scene.weather}. ${weatherText}`,
    `Time period: ${scene.period}. ${timeText}`,
    `Temperature: ${scene.tempMin}C~${scene.tempMax}C.`,
    `Landmarks: ${landmarks.join(", ")}.`,
    "Background融合 8 個當地知名景點，以微縮地景與童話城市的方式自然分布，不要像拼貼。",
    "Use 7-9 landmark anchors as recognizable city signals, arranged at different depths across the city panorama while keeping the composition clean and not overcrowded.",
    character,
    "The foreground main character should be cute, round-faced, big-eyed, expressive, and doing daily-life actions such as holding a small fan, drinking a cool beverage, shopping, walking, chatting, taking photos, or riding a tiny scooter.",
    "Add subtle visual motion cues suitable for a live wallpaper background: drifting clouds, tiny boats on water, walking poses, fluttering awnings, falling rain or snow when weather requires it, wind lines, sparkling highlights, and lively daily movement.",
    festival ? `Add local festival or seasonal atmosphere for ${festival}: natural festival details, seasonal plants, food, decorations, weather-sensitive mood, and cultural cues without turning the image into a poster.` : "If there is no local festival, keep the scene as everyday city life.",
    "Keep the upper sky area light, calm, open, and visually clean so phone time, date, and status widgets do not conflict.",
    "Do not write the city name anywhere in the image.",
    "Do not place a large title, header text, or location label in the sky.",
    isTaiwan ? "Small local shop signs may use Traditional Chinese styling only when they are natural environmental details." : "Small local shop signs may use local language styling only when they are natural environmental details.",
    "Do not draw phone UI, clock, date, battery, signal icons, app labels, or temperature widgets.",
    "Avoid text, logo, watermark, phone UI, large labels, and poster-like typography."
  ].join("\n");
}

function normalizeCharacter(value) {
  const clean = String(value || "person").trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (["cat", "貓"].includes(clean)) return "cat";
  if (["dog", "狗"].includes(clean)) return "dog";
  if (["hamster", "chinchilla", "hamster_chinchilla", "倉鼠", "仓鼠", "龍貓", "龙猫"].includes(clean)) return "hamster_chinchilla";
  return "person";
}

function normalizeStyle(value) {
  const clean = String(value || "knitted").trim().toLowerCase().replace(/[\s-]+/g, "_");
  return STYLE_ALIASES[clean] || "knitted";
}

function normalizeWeather(value) {
  const clean = String(value || "Cloudy").trim();
  if (SUPPORTED_WEATHERS.includes(clean)) return WEATHER_ALIASES[clean] || clean;
  return WEATHER_MAP[clean] || WEATHER_ALIASES[clean] || "多云";
}

function normalizePeriod(value) {
  const clean = String(value || "Afternoon").trim();
  if (DAILY_PERIODS.includes(clean)) return clean;
  return "Afternoon";
}

function characterPrompt(value) {
  switch (normalizeCharacter(value)) {
    case "cat":
      return "Main characters are varied cute Q-version cats: tabby cats, calico cats, black cats, white cats, orange cats, and fluffy round cats doing daily life actions.";
    case "hamster_chinchilla":
      return "Main characters are cute Q-version hamsters and chinchillas with round bodies, soft ears, tiny bags, and everyday city-life actions.";
    case "dog":
      return "Main characters are cute Q-version dogs of varied small breeds doing daily life actions, with friendly expressions and playful movement.";
    default:
      return "Main character is a cute Q-version girl with a round face and big eyes, wearing fresh summer clothes, smiling in the foreground, holding a small fan and an iced drink, joined by a few friendly city residents in daily-life actions.";
  }
}

function stylePrompt(value) {
  switch (normalizeStyle(value)) {
    case "colored_pencil":
      return "Use a refined colored pencil illustration style, soft paper grain, warm fairy-tale mood, clean depth, delicate hand-drawn strokes, gentle shading, and rich but soft color suitable for a phone live wallpaper.";
    default:
      return "Use a premium handmade knitted and crochet amigurumi style: yarn texture, soft fiber depth, plush miniature buildings, crochet clouds, stitched details, and cozy handcrafted lighting suitable for a phone live wallpaper.";
  }
}

function selectedLandmarks(landmarks) {
  const clean = (landmarks || [])
    .map((item) => String(item || "").trim())
    .filter(Boolean);
  if (clean.length <= 9) return clean;
  return clean.slice(0, 9);
}

async function generateImage(env, prompt) {
  const response = await fetch("https://api.openai.com/v1/images/generations", {
    method: "POST",
    headers: {
      "authorization": `Bearer ${env.OPENAI_API_KEY}`,
      "content-type": "application/json"
    },
    body: JSON.stringify({
      model: env.OPENAI_IMAGE_MODEL || "gpt-image-1",
      prompt,
      size: "1024x1536",
      n: 1
    })
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message || "OpenAI image generation failed");
  const b64 = body.data?.[0]?.b64_json;
  if (!b64) throw new Error("OpenAI response did not include b64_json");
  return Uint8Array.from(atob(b64), (char) => char.charCodeAt(0));
}

async function nextSequence(env, citySlug, date) {
  const prefix = `wallpapers/${citySlug}/${citySlug}_${date.replaceAll("-", "")}_`;
  const listed = await env.WALLPAPER_BUCKET.list({ prefix });
  const next = String((listed.objects?.length || 0) + 1).padStart(3, "0");
  return next;
}

function wallpaperObjectKey(scene, fileName) {
  return `wallpapers/${characterFolder(scene.character)}/${styleFolder(scene.style)}/${fileName}`;
}

function manifestObjectKey(scene, citySlug, id) {
  return `manifests/${characterFolder(scene.character)}/${styleFolder(scene.style)}/${citySlug}/${id}.json`;
}

function wallpaperFileName(scene, extension) {
  const parts = [
    normalizeFestival(scene.festival),
    filenamePart(scene.cityLocal || scene.city),
    characterLabel(scene.character),
    styleLabel(scene.style),
    filenamePart(scene.period),
    filenamePart(scene.weather)
  ].filter(Boolean);
  return `${parts.join("_")}${extension}`;
}

function characterFolder(value) {
  return normalizeCharacter(value);
}

function styleFolder(value) {
  return normalizeStyle(value);
}

function characterLabel(value) {
  switch (normalizeCharacter(value)) {
    case "cat":
      return "貓";
    case "dog":
      return "狗";
    case "hamster_chinchilla":
      return "倉鼠龍貓";
    default:
      return "人";
  }
}

function styleLabel(value) {
  switch (normalizeStyle(value)) {
    case "colored_pencil":
      return "色鉛筆";
    default:
      return "針織";
  }
}

function filenamePart(value) {
  return String(value || "")
    .trim()
    .replace(/[\\/:*?"<>|]+/g, "")
    .replace(/\s+/g, "")
    .slice(0, 60);
}

function normalizeFestival(value) {
  return filenamePart(value);
}

function festivalFor(country, date) {
  if (country !== "Taiwan") return "";
  const md = String(date || "").slice(5, 10);
  const festivals = {
    "01-01": "元旦",
    "02-14": "情人節",
    "03-08": "婦女節",
    "04-04": "兒童節",
    "05-01": "勞動節",
    "07-07": "小暑",
    "08-08": "父親節",
    "10-10": "國慶日",
    "12-25": "聖誕節"
  };
  return festivals[md] || "";
}

function weatherPrompt(weather) {
  if (weather.includes("晴")) return "晴朗炎熱天氣：柔和金色陽光、淡藍天空、蓬鬆白雲、微微熱氣、樹影與清亮高光。";
  if (weather.includes("雷")) return "Thunderstorm weather: dramatic layered clouds, distant lightning glow, rain motion, wet reflections, and cozy safe city lights.";
  if (weather.includes("雪")) return "Snowy weather: soft snowfall, powdery rooftops, cool highlights, warm windows, and quiet winter movement.";
  if (weather.includes("雨") || weather.includes("阵雨")) return "Rainy weather: gentle rain streaks, puddle reflections, umbrellas, wet streets, and soft diffused light.";
  if (weather.includes("雾") || weather.includes("霾") || weather.includes("尘") || weather.includes("沙")) return "Low-visibility weather: hazy air, muted depth layers, soft silhouettes, and gentle atmospheric diffusion.";
  if (weather.includes("阴") || weather.includes("云")) return "Cloudy weather: soft cloud cover, gentle light, calm shadows, and cozy color harmony.";
  return "Weather should be clearly reflected through sky, light, ground details, props, and character actions.";
}

function timePrompt(period) {
  switch (normalizePeriod(period)) {
    case "sunraise":
      return "sunraise: pale dawn light, gentle first sunlight, quiet streets, fresh air, and soft pastel sky.";
    case "Morning":
      return "Morning: fresh sunrise light, soft cool shadows, breakfast shops, and gentle city waking-up energy.";
    case "Afternoon":
      return "Afternoon: mellow warm light, relaxed daily pace, richer colors, and comfortable outdoor activity.";
    case "Sunset":
      return "Sunset: orange-pink sky, glowing windows, long shadows, and romantic warm atmosphere.";
    case "Night":
      return "Night: deep blue sky, warm street lights, glowing shop signs as small environmental details, and lively evening city life.";
    default:
      return "Midnight: quiet deep night, moonlit sky, soft lamps, peaceful streets, and dreamy calm atmosphere.";
  }
}

function fileUrl(url, objectKey) {
  return `${url.origin}/files/${encodeURIComponent(objectKey)}`;
}

function authorized(request, url, env, formToken = "") {
  const header = request.headers.get("authorization") || "";
  const bearer = header.toLowerCase().startsWith("bearer ") ? header.slice(7).trim() : "";
  const query = url.searchParams.get("token") || "";
  return safeEqual(bearer, env.MANUAL_UPLOAD_TOKEN)
    || safeEqual(query, env.MANUAL_UPLOAD_TOKEN)
    || safeEqual(formToken, env.MANUAL_UPLOAD_TOKEN);
}

function safeEqual(a, b) {
  a = String(a || "");
  b = String(b || "");
  if (!a || !b || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function stringValue(value, fallback) {
  if (value == null || typeof value !== "string") return fallback;
  const clean = value.trim();
  return clean ? clean : fallback;
}

function extensionFor(contentType) {
  if (contentType === "image/jpeg") return ".jpg";
  if (contentType === "image/webp") return ".webp";
  return ".png";
}

function html(markup, status = 200) {
  return new Response(markup, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function slug(value) {
  return (value || "city")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "city";
}

function hash(value) {
  let h = 0;
  for (let i = 0; i < value.length; i++) h = Math.imul(31, h) + value.charCodeAt(i) | 0;
  return Math.abs(h).toString(36);
}

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*"
    }
  });
}

function cors() {
  return new Response(null, {
    headers: {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET, OPTIONS",
      "access-control-allow-headers": "content-type"
    }
  });
}
