const WEATHER_MAP = {
  Clear: "Sunny",
  Clouds: "Cloudy",
  Rain: "Rainy",
  Drizzle: "Rainy",
  Thunderstorm: "Rainy",
  Snow: "Snowy",
  Mist: "Foggy",
  Fog: "Foggy",
  Haze: "Foggy",
  Smoke: "Foggy",
  Dust: "Foggy",
  Sand: "Foggy"
};
const PROMPT_VERSION = "open-sky-diorama-no-city-label-v5";
const DAILY_PERIODS = ["Morning", "Noon", "Sunset", "Evening", "DeepNight"];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return cors();
    if (env.WALLPAPER_BUCKET) {
      ctx.waitUntil(cleanupExpired(env));
    }
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
        "/?city=Kaohsiung&country=Taiwan&date=2026-06-10&weather=Rainy&period=Noon",
        "/admin/upload"
      ]
    });
  },

  async scheduled(event, env, ctx) {
    if (env.WALLPAPER_BUCKET) {
      ctx.waitUntil(cleanupExpired(env));
    }
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
    period: normalizePeriod(stringValue(form.get("period"), "Noon")),
    character: normalizeCharacter(stringValue(form.get("character"), "person")),
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
  <p><label>Weather<br><select name="weather" style="width:100%;padding:10px"><option>Sunny</option><option selected>Cloudy</option><option>Rainy</option><option>Snowy</option><option>Foggy</option></select></label></p>
  <p><label>Period<br><select name="period" style="width:100%;padding:10px"><option>Morning</option><option selected>Noon</option><option>Sunset</option><option>Evening</option><option>DeepNight</option></select></label></p>
  <p><label>Character<br><select name="character" style="width:100%;padding:10px"><option value="person">人</option><option value="cat">貓</option><option value="hamster">倉鼠</option><option value="dog">狗</option><option value="parrot">鸚鵡</option></select></label></p>
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
  const sequence = await nextSequence(env, citySlug, scene.date);
  const extension = extensionFor(contentType);
  const fileName = `${citySlug}_${scene.date.replaceAll("-", "")}_${sequence}${extension}`;
  const objectKey = `wallpapers/${citySlug}/${fileName}`;
  const sceneKey = [citySlug, scene.country, scene.date, scene.weather, scene.period, scene.character, "manual-upload"].join("|");
  const bytes = await image.arrayBuffer();
  await env.WALLPAPER_BUCKET.put(objectKey, bytes, {
    httpMetadata: { contentType },
    customMetadata: {
      city: scene.city,
      country: scene.country,
      weather: scene.weather,
      period: scene.period,
      character: scene.character,
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
    date: scene.date,
    scene_key: sceneKey,
    source: "manual-upload",
    animation: {
      type: "android-live-wallpaper-overlay",
      weather: scene.weather,
      period: scene.period
    }
  };
  const manifestKey = `manifests/${citySlug}/manual-${hash(sceneKey + "|" + fileName)}.json`;
  await env.WALLPAPER_BUCKET.put(manifestKey, JSON.stringify(manifest), {
    httpMetadata: { contentType: "application/json; charset=utf-8" }
  });
  return {
    ...manifest,
    image_url: fileUrl(url, objectKey),
    reused: false,
    expires_at: expiresAt(new Date(), env)
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
  const result = await ensureWallpaper(env, url, scene, { allowLatest: !force, force, ctx });
  return json(result);
}

async function ensureWallpaper(env, url, scene, options = {}) {
  const citySlug = slug(scene.city);
  const sceneKey = [citySlug, scene.country, scene.date, scene.weather, scene.period, scene.character, PROMPT_VERSION].join("|");
  const manifestKey = `manifests/${citySlug}/${hash(sceneKey)}.json`;
  const existing = options.force ? null : await env.WALLPAPER_BUCKET.get(manifestKey);
  if (existing) {
    const manifest = await existing.json();
    const existingImage = await env.WALLPAPER_BUCKET.get(manifest.object_key);
    if (!existingImage || isExpired(existingImage.uploaded, env)) {
      await env.WALLPAPER_BUCKET.delete(manifestKey);
      if (existingImage) await env.WALLPAPER_BUCKET.delete(manifest.object_key);
    } else {
      return {
        ...manifest,
        image_url: fileUrl(url, manifest.object_key),
        reused: true,
        expires_at: expiresAt(existingImage.uploaded, env)
      };
    }
  }

  if (options.allowLatest) {
    const latest = await latestCityWallpaper(env, url, citySlug);
    if (latest) {
      if (options.ctx) {
        options.ctx.waitUntil(createWallpaper(env, url, scene, citySlug, sceneKey, manifestKey));
      }
      return {
        ...latest,
        scene_key: sceneKey,
        requested_weather: scene.weather,
        requested_period: scene.period,
        reused: true,
        pending_refresh: true
      };
    }
  }

  return createWallpaper(env, url, scene, citySlug, sceneKey, manifestKey);
}

async function createWallpaper(env, url, scene, citySlug, sceneKey, manifestKey) {
  const sequence = await nextSequence(env, citySlug, scene.date);
  const fileName = `${citySlug}_${scene.date.replaceAll("-", "")}_${sequence}.png`;
  const objectKey = `wallpapers/${citySlug}/${fileName}`;
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
    expires_at: expiresAt(new Date(), env)
  };
}

async function latestCityWallpaper(env, url, citySlug) {
  const listed = await env.WALLPAPER_BUCKET.list({
    prefix: `wallpapers/${citySlug}/`,
    limit: 100
  });
  const objects = (listed.objects || [])
    .filter((object) => !isExpired(object.uploaded, env))
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
    date: metadata.date || "",
    image_url: fileUrl(url, object.key),
    expires_at: expiresAt(object.uploaded, env)
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
      for (const period of DAILY_PERIODS) {
        const scene = {
          city: city.city,
          cityLocal: city.cityLocal || city.city,
          country: city.country || "Taiwan",
          date: todayForOffset(city.utcOffset || 8),
          weather: weatherInfo.weather,
          period,
          tempMin: String(Math.round(weatherInfo.temp_min)),
          tempMax: String(Math.round(weatherInfo.temp_max)),
          landmarks: city.landmarks || ["central station", "old town market", "city park"]
        };
        await ensureWallpaper(env, url, scene);
      }
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
  if (hour >= 5 && hour <= 10) return "Morning";
  if (hour >= 11 && hour <= 14) return "Noon";
  if (hour >= 17 && hour <= 18) return "Sunset";
  if (hour >= 19 && hour <= 22) return "Evening";
  return "DeepNight";
}

function shiftedDate(offset) {
  return new Date(Date.now() + offset * 60 * 60 * 1000);
}

async function serveFile(url, env) {
  if (!env.WALLPAPER_BUCKET) return json({ error: "WALLPAPER_BUCKET R2 binding is not configured" }, 500);
  const key = decodeURIComponent(url.pathname.replace(/^\/files\//, ""));
  const object = await env.WALLPAPER_BUCKET.get(key);
  if (!object) return json({ error: "File not found" }, 404);
  if (isExpired(object.uploaded, env)) {
    await env.WALLPAPER_BUCKET.delete(key);
    return json({ error: "File expired" }, 404);
  }
  return new Response(object.body, {
    headers: {
      "content-type": object.httpMetadata?.contentType || "application/octet-stream",
      "cache-control": "public, max-age=86400",
      "expires": expiresAt(object.uploaded, env),
      "access-control-allow-origin": "*"
    }
  });
}

async function cleanupExpired(env) {
  await cleanupPrefix(env, "wallpapers/");
  await cleanupPrefix(env, "manifests/");
}

async function cleanupPrefix(env, prefix) {
  let cursor;
  do {
    const listed = await env.WALLPAPER_BUCKET.list({ prefix, cursor, limit: 100 });
    const expired = (listed.objects || [])
      .filter((object) => isExpired(object.uploaded, env))
      .map((object) => object.key);
    if (expired.length) await env.WALLPAPER_BUCKET.delete(expired);
    cursor = listed.truncated ? listed.cursor : undefined;
  } while (cursor);
}

function retentionMs(env) {
  const hours = Number(env.WALLPAPER_RETENTION_HOURS || 24);
  return Math.max(1, hours) * 60 * 60 * 1000;
}

function isExpired(uploaded, env) {
  if (!uploaded) return false;
  return Date.now() - new Date(uploaded).getTime() > retentionMs(env);
}

function expiresAt(uploaded, env) {
  return new Date(new Date(uploaded).getTime() + retentionMs(env)).toUTCString();
}

function readScene(url) {
  const landmarks = (url.searchParams.get("landmarks") || "")
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);
  return {
    city: url.searchParams.get("city") || "Kaohsiung",
    cityLocal: url.searchParams.get("cityLocal") || url.searchParams.get("city") || "Kaohsiung",
    country: url.searchParams.get("country") || "Taiwan",
    date: url.searchParams.get("date") || new Date().toISOString().slice(0, 10),
    weather: url.searchParams.get("weather") || "Cloudy",
    period: url.searchParams.get("period") || "Noon",
    character: normalizeCharacter(url.searchParams.get("character") || "person"),
    tempMin: url.searchParams.get("tempMin") || "27",
    tempMax: url.searchParams.get("tempMax") || "32",
    landmarks: landmarks.length ? landmarks : ["central station", "old town market", "city park"]
  };
}

function buildPrompt(scene) {
  const isTaiwan = scene.country === "Taiwan";
  const landmarks = selectedLandmarks(scene.landmarks);
  const character = characterPrompt(scene.character);
  return [
    "Create a premium 9:16 Android live wallpaper background in miniature Amigurumi crochet diorama style.",
    "Match this art direction: bright open sky, airy daylight, crisp dimensional crochet stitches, miniature toy-city depth, clean composition, charming handcrafted detail, soft warm color, and a lively travel-postcard feeling.",
    "Avoid flat felt texture, muddy gray haze, dull low-contrast lighting, oversized text, cropped faces, empty foreground, and simple blocky buildings.",
    "Use only city or county-level geography. Do not depict districts, townships, streets, neighborhoods, or overly specific local areas.",
    `City: ${scene.city}. Country: ${scene.country}.`,
    `Weather: ${scene.weather}. Time period: ${scene.period}. Temperature: ${scene.tempMin}C~${scene.tempMax}C.`,
    `Landmarks: ${landmarks.join(", ")}.`,
    "Use only these 2-3 landmark anchors as recognizable city signals; do not crowd the image with too many landmarks.",
    "All buildings, vehicles, shops, trees, rivers, boats, paths, and roads are handmade crochet toys with visible yarn loops and plush depth.",
    character,
    "Characters should look active and varied, with poses that imply motion and daily life instead of standing still.",
    "Add subtle visual motion cues suitable for a live wallpaper background: drifting crochet clouds, tiny boats on water, scooter movement, walking poses, fluttering shop awnings, falling rain or snow when weather requires it.",
    "Keep the upper sky area light, calm, open, and visually clean so phone time, date, and status widgets do not conflict.",
    "Do not write the city name anywhere in the image.",
    "Do not place a large title, header text, or location label in the sky.",
    "Use a legible high-contrast but gentle yarn color that remains visible on the lighter sky without clashing with the crochet artwork.",
    isTaiwan ? "Small local shop signs may use Traditional Chinese styling only when they are natural environmental details." : "Small local shop signs may use local language styling only when they are natural environmental details.",
    "Do not draw phone UI, clock, date, battery, signal icons, app labels, or temperature widgets.",
    "No large readable headline text."
  ].join("\n");
}

function normalizeCharacter(value) {
  const clean = String(value || "person").trim().toLowerCase();
  if (["cat", "hamster", "dog", "parrot"].includes(clean)) return clean;
  return "person";
}

function normalizeWeather(value) {
  const clean = String(value || "Cloudy").trim();
  if (["Sunny", "Cloudy", "Rainy", "Snowy", "Foggy"].includes(clean)) return clean;
  return WEATHER_MAP[clean] || "Cloudy";
}

function normalizePeriod(value) {
  const clean = String(value || "Noon").trim();
  if (DAILY_PERIODS.includes(clean)) return clean;
  return "Noon";
}

function characterPrompt(value) {
  switch (normalizeCharacter(value)) {
    case "cat":
      return "Main characters are cute chibi Amigurumi cats doing daily life actions: walking, chatting, shopping, riding scooters, taking photos, and enjoying the city.";
    case "hamster":
      return "Main characters are cute chibi Amigurumi hamsters doing daily life actions: walking, chatting, shopping, riding scooters, taking photos, and enjoying the city.";
    case "dog":
      return "Main characters are cute chibi Amigurumi dogs doing daily life actions: walking, chatting, shopping, riding scooters, taking photos, and enjoying the city.";
    case "parrot":
      return "Main characters are cute chibi Amigurumi parrots doing daily life actions: walking, chatting, shopping, riding scooters, taking photos, and enjoying the city.";
    default:
      return "Main characters are cute chibi Amigurumi people doing daily life actions: commuting, buying breakfast or drinks, walking with umbrellas, chatting, taking photos, riding scooters, visiting shops, relaxing in a park, or browsing a night market.";
  }
}

function selectedLandmarks(landmarks) {
  const clean = (landmarks || [])
    .map((item) => String(item || "").trim())
    .filter(Boolean);
  if (clean.length <= 3) return clean;
  return [clean[0], clean[1], clean[2]];
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
