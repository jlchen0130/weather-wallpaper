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
const PROMPT_VERSION = "sky-city-label-v2";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return cors();
    if (env.WALLPAPER_BUCKET) {
      ctx.waitUntil(cleanupExpired(env));
    }
    if (url.pathname.startsWith("/files/")) return serveFile(url, env);
    if (url.searchParams.has("lat") && url.searchParams.has("lon") && !url.searchParams.has("city")) {
      return weather(request, env);
    }
    if (url.searchParams.has("city")) return wallpaper(request, env);
    return json({
      service: "amigurumi-theme-server",
      routes: [
        "/?lat=22.6273&lon=120.3014&units=metric",
        "/?city=Kaohsiung&country=Taiwan&date=2026-06-10&weather=Rainy&period=Afternoon"
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

async function wallpaper(request, env) {
  if (!env.WALLPAPER_BUCKET) return json({ error: "WALLPAPER_BUCKET R2 binding is not configured" }, 500);
  if (!env.OPENAI_API_KEY) return json({ error: "OPENAI_API_KEY is not configured" }, 500);

  const url = new URL(request.url);
  const scene = readScene(url);
  const result = await ensureWallpaper(env, url, scene);
  return json(result);
}

async function ensureWallpaper(env, url, scene) {
  const citySlug = slug(scene.city);
  const sceneKey = [citySlug, scene.country, scene.weather, scene.period, PROMPT_VERSION].join("|");
  const manifestKey = `manifests/${citySlug}/${hash(sceneKey)}.json`;
  const existing = await env.WALLPAPER_BUCKET.get(manifestKey);
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

  const sequence = await nextSequence(env, citySlug, scene.date);
  const fileName = `${citySlug}_${scene.date.replaceAll("-", "")}_${sequence}.png`;
  const objectKey = `wallpapers/${citySlug}/${fileName}`;
  const prompt = buildPrompt(scene);
  const imageBytes = await generateImage(env, prompt);
  await env.WALLPAPER_BUCKET.put(objectKey, imageBytes, {
    httpMetadata: { contentType: "image/png" },
    customMetadata: {
      city: scene.city,
      weather: scene.weather,
      period: scene.period,
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
        tempMin: String(Math.round(weatherInfo.temp_min)),
        tempMax: String(Math.round(weatherInfo.temp_max)),
        landmarks: city.landmarks || ["central station", "old town market", "city park"]
      };
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
      landmarks: ["85 Sky Tower", "Love River", "Pier-2 Art Center"]
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
  if (hour >= 11 && hour <= 16) return "Afternoon";
  if (hour >= 17 && hour <= 18) return "Sunset";
  if (hour >= 19 && hour <= 21) return "Evening";
  return "Night";
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
    period: url.searchParams.get("period") || "Afternoon",
    tempMin: url.searchParams.get("tempMin") || "27",
    tempMax: url.searchParams.get("tempMax") || "32",
    landmarks: landmarks.length ? landmarks : ["central station", "old town market", "city park"]
  };
}

function buildPrompt(scene) {
  const isTaiwan = scene.country === "Taiwan";
  const label = isTaiwan ? scene.cityLocal : scene.city;
  return [
    "Create a premium 9:16 Android wallpaper in miniature Amigurumi crochet style.",
    `City: ${scene.city}. Country: ${scene.country}.`,
    `Weather: ${scene.weather}. Time period: ${scene.period}. Temperature: ${scene.tempMin}C~${scene.tempMax}C.`,
    `Landmarks: ${scene.landmarks.join(", ")}.`,
    "All buildings, vehicles, people, shops, trees, and roads are handmade crochet toys.",
    "Keep the upper sky area light, calm, and visually clean so phone time, date, and status widgets do not conflict.",
    `Place one clear city name label in the pale open sky area: ${label}.`,
    "The city label should look embroidered with yarn, large enough to read, centered or upper-center, and must not overlap buildings, people, clouds, rain, or lock-screen widgets.",
    "Use a legible high-contrast but gentle yarn color that remains visible on the lighter sky without clashing with the crochet artwork.",
    isTaiwan ? "Use Traditional Chinese styling for local shop signs." : "Use English for the city name label.",
    "Do not draw phone UI, clock, date, battery, signal icons, app labels, or temperature widgets.",
    "No extra readable text beyond the city name label."
  ].join("\n");
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
