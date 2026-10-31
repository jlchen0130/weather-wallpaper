const DEFAULT_STYLE = "knitted";
const DEFAULT_CHARACTER = "person";
const DEFAULT_PERIOD = "afternoon";
const DEFAULT_WEATHER = "cloudy";
const DEFAULT_CITY = "Kaohsiung";
const MANUAL_UPLOAD_MAX_BYTES = 12 * 1024 * 1024;
const MANUAL_UPLOAD_MAX_REQUEST_BYTES = MANUAL_UPLOAD_MAX_BYTES + 256 * 1024;
const SCHEDULED_CITIES = ["Kaohsiung", "Taipei"];
const SUPPORTED_STYLES = ["knitted", "colored_pencil"];
const SUPPORTED_CHARACTERS = ["person", "cat", "dog", "hamster_chinchilla", "parrot"];
const CANONICAL_WEATHERS = new Set([
  "sunny", "partly_cloudy", "cloudy", "overcast", "light_rain", "heavy_rain",
  "typhoon", "fog", "haze", "strong_wind", "thunder_shower", "thunderstorm",
  "heatwave", "cold_wave"
]);

const TAIWAN_CITY_ALIASES = {
  taipei: "Taipei",
  "台北": "Taipei",
  "台北市": "Taipei",
  "臺北": "Taipei",
  "臺北市": "Taipei",
  newtaipei: "NewTaipei",
  "new taipei": "NewTaipei",
  "新北": "NewTaipei",
  "新北市": "NewTaipei",
  taoyuan: "Taoyuan",
  "桃園": "Taoyuan",
  "桃園市": "Taoyuan",
  taichung: "Taichung",
  "台中": "Taichung",
  "台中市": "Taichung",
  "臺中": "Taichung",
  "臺中市": "Taichung",
  tainan: "Tainan",
  "台南": "Tainan",
  "台南市": "Tainan",
  "臺南": "Tainan",
  "臺南市": "Tainan",
  kaohsiung: "Kaohsiung",
  "高雄": "Kaohsiung",
  "高雄市": "Kaohsiung",
  keelung: "Keelung",
  "基隆": "Keelung",
  "基隆市": "Keelung",
  hsinchu: "Hsinchu",
  "新竹": "Hsinchu",
  hsinchucity: "HsinchuCity",
  hsinchucounty: "HsinchuCounty",
  "新竹市": "HsinchuCity",
  "新竹縣": "HsinchuCounty",
  miaoli: "Miaoli",
  "苗栗": "Miaoli",
  "苗栗縣": "Miaoli",
  changhua: "Changhua",
  "彰化": "Changhua",
  "彰化縣": "Changhua",
  nantou: "Nantou",
  "南投": "Nantou",
  "南投縣": "Nantou",
  yunlin: "Yunlin",
  "雲林": "Yunlin",
  "雲林縣": "Yunlin",
  chiayi: "Chiayi",
  "嘉義": "Chiayi",
  chiayicity: "ChiayiCity",
  chiayicounty: "ChiayiCounty",
  "嘉義市": "ChiayiCity",
  "嘉義縣": "ChiayiCounty",
  pingtung: "Pingtung",
  "屏東": "Pingtung",
  "屏東縣": "Pingtung",
  yilan: "Yilan",
  "宜蘭": "Yilan",
  "宜蘭縣": "Yilan",
  hualien: "Hualien",
  "花蓮": "Hualien",
  "花蓮縣": "Hualien",
  taitung: "Taitung",
  "台東": "Taitung",
  "台東縣": "Taitung",
  "臺東": "Taitung",
  "臺東縣": "Taitung",
  penghu: "Penghu",
  "澎湖": "Penghu",
  "澎湖縣": "Penghu",
  kinmen: "Kinmen",
  "金門": "Kinmen",
  "金門縣": "Kinmen",
  lienchiang: "Lienchiang",
  "連江": "Lienchiang",
  "連江縣": "Lienchiang",
  matzu: "Lienchiang",
  "馬祖": "Lienchiang"
};

const STYLE_ALIASES = {
  knitted: "knitted",
  knit: "knitted",
  crochet: "knitted",
  amigurumi: "knitted",
  "針織": "knitted",
  "鉤針": "knitted",
  "編織": "knitted",
  colored_pencil: "colored_pencil",
  color_pencil: "colored_pencil",
  pencil: "colored_pencil",
  pastel_pencil: "colored_pencil",
  "色鉛筆": "colored_pencil",
  "彩色鉛筆": "colored_pencil",
  "粉鉛筆": "colored_pencil"
};

const CHARACTER_ALIASES = {
  person: "person",
  human: "person",
  girl: "person",
  people: "person",
  "人": "person",
  "人物": "person",
  cat: "cat",
  "貓": "cat",
  "猫": "cat",
  dog: "dog",
  "狗": "dog",
  hamster: "hamster_chinchilla",
  chinchilla: "hamster_chinchilla",
  hamster_chinchilla: "hamster_chinchilla",
  "倉鼠": "hamster_chinchilla",
  "仓鼠": "hamster_chinchilla",
  "龍貓": "hamster_chinchilla",
  "龙猫": "hamster_chinchilla",
  parrot: "parrot",
  bird: "parrot",
  "鸚鵡": "parrot",
  "鹦鹉": "parrot"
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    try {
      if (request.method === "OPTIONS") return cors();
      if (url.pathname.startsWith("/files/")) return serveR2File(url, env);
      if (url.pathname === "/admin/upload") return adminUploadResponse(request, env);
      if (url.pathname === "/health") return json({ ok: true, service: "weather-wallpaper-server" });
      if (isWeatherRequest(url)) return weatherCompatibilityResponse(url, env);
      if (isWallpaperRequest(url)) return wallpaperResponse(request, env);
      return json({
        service: "weather-wallpaper-server",
        compatible_params: ["loc", "city", "cityLocal", "weather", "period", "char", "character", "style"],
        asset_policy: "manual-png-only",
        object_key_format: "wallpaper/<style>/<char>/<festival>_<city>_<char>_<period>_<weather>.png"
      });
    } catch (error) {
      waitUntilSafe(ctx, sendTelegramAlert(env, {
        title: "Worker unhandled exception",
        error,
        scene: safeSceneFromUrl(url)
      }));
      return notModified("worker_exception");
    }
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(auditScheduledCoverage(event, env).catch((error) => {
      console.error(JSON.stringify({
        level: "error",
        event: "scheduled_wallpaper_coverage_failed",
        message: error?.message || String(error)
      }));
    }));
  }
};

async function wallpaperResponse(request, env) {
  assertBinding(env.WALLPAPER_BUCKET, "WALLPAPER_BUCKET");
  const url = new URL(request.url);
  const scene = await completeScene(parseClientScene(url), url, env);
  scene.period = wallpaperPeriod(scene);
  const objectKey = buildWallpaperKey(scene, "png");
  const cached = await env.WALLPAPER_BUCKET.get(objectKey);

  if (cached) return wallpaperJson(url, scene, objectKey, true);
  if (scene.festival !== "none") {
    const baseScene = { ...scene, festival: "none" };
    const baseKey = buildWallpaperKey(baseScene, "png");
    if (await env.WALLPAPER_BUCKET.get(baseKey)) return wallpaperJson(url, baseScene, baseKey, true);
  }
  if (scene.style !== "knitted" || scene.character !== "person") {
    const legacyWeather = {
      partly_cloudy: "cloudy", overcast: "cloudy", fog: "cloudy", haze: "cloudy",
      light_rain: "rainy", heavy_rain: "rainy", thunder_shower: "thunder", thunderstorm: "thunder"
    }[scene.weather];
    const legacyCity = { HsinchuCity: "Hsinchu", HsinchuCounty: "Hsinchu",
      ChiayiCity: "Chiayi", ChiayiCounty: "Chiayi" }[scene.city];
    if (legacyWeather || legacyCity) {
      for (const festival of new Set([scene.festival, "none"])) {
        const legacyScene = { ...scene, festival, city: legacyCity || scene.city,
          weather: legacyWeather || scene.weather };
        const legacyKey = buildWallpaperKey(legacyScene, "png");
        if (await env.WALLPAPER_BUCKET.get(legacyKey)) return wallpaperJson(url, legacyScene, legacyKey, true);
      }
    }
  }
  return notModified("manual_wallpaper_missing_keep_current_wallpaper");
}

async function adminUploadResponse(request, env) {
  assertBinding(env.WALLPAPER_BUCKET, "WALLPAPER_BUCKET");
  if (request.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const expectedToken = env.MANUAL_UPLOAD_TOKEN || env.ADMIN_UPLOAD_TOKEN || "";
  if (!expectedToken) return json({ error: "Manual upload token is not configured" }, 503);

  const requestContentType = request.headers.get("content-type") || "";
  if (!requestContentType.toLowerCase().includes("multipart/form-data")) {
    return json({ error: "Expected multipart/form-data upload" }, 400);
  }

  const contentLength = Number(request.headers.get("content-length") || 0);
  if (Number.isFinite(contentLength) && contentLength > MANUAL_UPLOAD_MAX_REQUEST_BYTES) {
    return json({ error: "PNG upload exceeds the 12 MiB limit" }, 413);
  }

  const form = await request.formData();
  const providedToken = String(form.get("token") || "");
  if (!await timingSafeEqual(providedToken, expectedToken)) return json({ error: "Unauthorized" }, 401);

  const image = form.get("image");
  if (!image || typeof image.arrayBuffer !== "function") {
    return json({ error: "Missing image file" }, 400);
  }

  if (String(image.type || "").toLowerCase() !== "image/png") {
    return json({ error: "Only image/png uploads are accepted" }, 415);
  }
  if (!Number.isFinite(image.size) || image.size <= 0) return json({ error: "PNG file is empty" }, 400);
  if (image.size > MANUAL_UPLOAD_MAX_BYTES) return json({ error: "PNG upload exceeds the 12 MiB limit" }, 413);

  const scene = parseAdminScene(form);
  const objectKey = buildWallpaperKey(scene, "png");
  const bytes = await image.arrayBuffer();
  if (!hasPngSignature(bytes)) return json({ error: "Uploaded file is not a valid PNG" }, 415);

  await env.WALLPAPER_BUCKET.put(objectKey, bytes, {
    httpMetadata: { contentType: "image/png" },
    customMetadata: {
      style: scene.style,
      festival: scene.festival,
      character: scene.character,
      city: scene.city,
      period: scene.period,
      weather: scene.weather,
      source: "manual-chatgpt-upload",
      uploadedDate: currentDateKey(),
      uploadedAt: new Date().toISOString()
    }
  });

  return wallpaperJson(new URL(request.url), scene, objectKey, false, "manual_uploaded");
}

function parseClientScene(url) {
  const rawLoc = firstParam(url, ["loc", "city", "cityEnglish", "cityLocal", "location"]) || DEFAULT_CITY;
  const city = normalizeCity(rawLoc);
  const weather = normalizeWeather(firstParam(url, ["weather", "weatherMain", "condition"]) || DEFAULT_WEATHER);
  const period = normalizePeriod(firstParam(url, ["period", "timePeriod", "time"]) || DEFAULT_PERIOD);
  const character = normalizeCharacter(firstParam(url, ["char", "character"]) || DEFAULT_CHARACTER);
  const style = normalizeStyle(firstParam(url, ["style", "themeStyle"]) || DEFAULT_STYLE);
  const festival = detectFestival(new Date());
  return { city, weather, period, character, style, festival };
}

async function completeScene(scene, url, env) {
  if (url.searchParams.get("serverWeather") !== "1") return scene;
  const serverWeather = await fetchServerWeather(scene, url, env);
  return {
    ...scene,
    weather: serverWeather || scene.weather,
    period: currentServerPeriod()
  };
}

async function fetchServerWeather(scene, url, env) {
  if (!env.OPENWEATHER_API_KEY) return "";
  try {
    const api = new URL("https://api.openweathermap.org/data/2.5/weather");
    const lat = url.searchParams.get("lat");
    const lon = url.searchParams.get("lon");
    if (lat && lon) {
      api.searchParams.set("lat", lat);
      api.searchParams.set("lon", lon);
    } else {
      api.searchParams.set("q", `${scene.city},TW`);
    }
    api.searchParams.set("units", "metric");
    api.searchParams.set("appid", env.OPENWEATHER_API_KEY);
    const response = await fetch(api);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      console.log(JSON.stringify({ level: "warn", event: "server_weather_failed", city: scene.city, status: response.status }));
      return "";
    }
    const condition = body?.weather?.[0];
    if (!condition) return "";
    const id = Number(condition.id);
    if (id === 800) return "sunny";
    if (id === 801 || id === 802) return "partly_cloudy";
    if (id === 803) return "cloudy";
    if (id === 804) return "overcast";
    if (id >= 200 && id <= 299) return [200, 201, 202, 230, 231, 232].includes(id)
      ? "thunder_shower" : "thunderstorm";
    if ([502, 503, 504, 522, 531].includes(id)) return "heavy_rain";
    if (id >= 300 && id <= 599) return "light_rain";
    if (id === 701 || id === 741) return "fog";
    if ([711, 721, 731, 751, 761, 762].includes(id)) return "haze";
    if (id === 771) return "strong_wind";
    if (id === 781) return "typhoon";
    return normalizeWeather(condition.description || condition.main || "");
  } catch (error) {
    console.log(JSON.stringify({ level: "warn", event: "server_weather_exception", city: scene.city, message: error?.message || String(error) }));
    return "";
  }
}

function currentServerPeriod(date = new Date()) {
  const hour = Number(new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Taipei",
    hour: "2-digit",
    hour12: false
  }).format(date));
  if (hour >= 4 && hour <= 6) return "sunrise";
  if (hour >= 7 && hour <= 10) return "morning";
  if (hour >= 11 && hour <= 15) return "afternoon";
  if (hour >= 16 && hour <= 18) return "sunset";
  if (hour >= 19 && hour <= 22) return "night";
  return "midnight";
}

function buildWallpaperKey(scene, extension = "png") {
  const fileName = [
    scene.festival,
    scene.city,
    scene.character,
    wallpaperPeriod(scene),
    scene.weather
  ].map(filenamePart).join("_");
  return `wallpaper/${filenamePart(scene.style)}/${filenamePart(scene.character)}/${fileName}.${filenamePart(extension)}`;
}

function wallpaperPeriod(scene) {
  // The knitted-person collection has time variants only for sun-visible weather.
  return scene.style === "knitted" && scene.character === "person"
    && !["sunny", "partly_cloudy"].includes(scene.weather) ? "all_day" : scene.period;
}

async function auditScheduledCoverage(event, env) {
  assertBinding(env.WALLPAPER_BUCKET, "WALLPAPER_BUCKET");
  const scheduledAt = new Date(event.scheduledTime || Date.now());
  const period = currentServerPeriod(scheduledAt);
  const festival = detectFestival(scheduledAt);
  const missing = [];
  let available = 0;

  for (const city of SCHEDULED_CITIES) {
    const weatherUrl = new URL(`https://scheduled.invalid/?city=${encodeURIComponent(city)}`);
    const weather = await fetchServerWeather({ city }, weatherUrl, env) || DEFAULT_WEATHER;
    for (const style of SUPPORTED_STYLES) {
      for (const character of SUPPORTED_CHARACTERS) {
        const scene = { city, weather, period, character, style, festival };
        const objectKey = buildWallpaperKey(scene, "png");
        const object = await env.WALLPAPER_BUCKET.head(objectKey);
        if (object) available += 1;
        else missing.push(objectKey);
      }
    }
  }

  console.log(JSON.stringify({
    level: missing.length ? "warn" : "info",
    event: "scheduled_wallpaper_coverage",
    cron: event.cron,
    scheduledTime: event.scheduledTime,
    period,
    available,
    missingCount: missing.length,
    missing
  }));
}

function currentDateKey() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function wallpaperJson(url, scene, objectKey, reused, cache = null) {
  return json({
    file_name: objectKey.split("/").pop(),
    object_key: objectKey,
    image_url: fileUrl(url, objectKey),
    content_type: "image/png",
    asset_kind: "manual_png",
    reused,
    cache: cache || "hit",
    city: scene.city,
    weather: scene.weather,
    period: scene.period,
    character: scene.character,
    style: scene.style,
    festival: scene.festival,
    animation: {
      type: "android-live-wallpaper-overlay",
      source_format: "png",
      note: "The Android WallpaperService animates weather overlays above this PNG background."
    }
  });
}

async function serveR2File(url, env) {
  assertBinding(env.WALLPAPER_BUCKET, "WALLPAPER_BUCKET");
  const key = decodeURIComponent(url.pathname.replace(/^\/files\//, ""));
  if (!key.startsWith("wallpaper/")) return json({ error: "File not found" }, 404);
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

async function weatherCompatibilityResponse(url, env) {
  if (env.OPENWEATHER_API_KEY) {
    try {
      const api = new URL("https://api.openweathermap.org/data/2.5/weather");
      api.searchParams.set("lat", url.searchParams.get("lat"));
      api.searchParams.set("lon", url.searchParams.get("lon"));
      api.searchParams.set("units", url.searchParams.get("units") || "metric");
      api.searchParams.set("appid", env.OPENWEATHER_API_KEY);
      const response = await fetch(api);
      const body = await response.json();
      if (response.ok) {
        return json({
          weather: normalizeWeather(body?.weather?.[0]?.main || DEFAULT_WEATHER),
          temp_min: body?.main?.temp_min ?? 27,
          temp_max: body?.main?.temp_max ?? 32,
          city: body?.name || "",
          country: body?.sys?.country || ""
        });
      }
    } catch (error) {
      console.log(JSON.stringify({ level: "warn", event: "openweather_failed", message: error.message }));
    }
  }
  return json({
    weather: DEFAULT_WEATHER,
    temp_min: 27,
    temp_max: 32,
    city: "",
    country: ""
  });
}

async function sendTelegramAlert(env, alert) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return;
  const scene = alert.scene || {};
  const text = [
    `*${escapeTelegram(alert.title || "Wallpaper server alert")}*`,
    `*Error:* ${escapeTelegram(alert.error?.message || String(alert.error || "unknown"))}`,
    `*Style:* ${escapeTelegram(scene.style || "unknown")}`,
    `*City:* ${escapeTelegram(scene.city || "unknown")}`,
    `*Period:* ${escapeTelegram(scene.period || "unknown")}`,
    `*Weather:* ${escapeTelegram(scene.weather || "unknown")}`
  ].join("\n");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    signal: controller.signal,
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      chat_id: env.TELEGRAM_CHAT_ID,
      text,
      parse_mode: "MarkdownV2",
      disable_web_page_preview: true
    })
  }).finally(() => clearTimeout(timeout));
  if (!response.ok) {
    console.log(JSON.stringify({ level: "warn", event: "telegram_alert_failed", status: response.status }));
  }
}

function waitUntilSafe(ctx, promise) {
  ctx.waitUntil(Promise.resolve(promise).catch((error) => {
    console.log(JSON.stringify({
      level: "warn",
      event: "wait_until_failed",
      message: error?.message || String(error)
    }));
  }));
}

function normalizeCity(value) {
  const raw = String(value || DEFAULT_CITY).trim();
  const compact = raw.replace(/\s+/g, " ").replace(/[縣市]$/u, "");
  const keys = [
    raw,
    raw.toLowerCase(),
    raw.replace(/\s+/g, "").toLowerCase(),
    compact,
    compact.toLowerCase(),
    compact.replace(/\s+/g, "").toLowerCase()
  ];
  for (const key of keys) {
    if (TAIWAN_CITY_ALIASES[key]) return TAIWAN_CITY_ALIASES[key];
  }
  const ascii = raw.normalize("NFKD").replace(/[^\w\s-]/g, "").trim();
  return filenamePart(ascii || DEFAULT_CITY);
}

function normalizeWeather(value) {
  const clean = String(value || DEFAULT_WEATHER).trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (CANONICAL_WEATHERS.has(clean)) return clean;
  if (/(torrential|heavy|豪|暴|大雨)/i.test(clean) && /rain|雨/i.test(clean)) return "heavy_rain";
  if (/(typhoon|hurricane|cyclone|tropical[_\s]*storm|tornado|颱風|台风)/i.test(clean)) return "typhoon";
  if (/(thunder|storm|雷|閃電|闪电|hail|冰雹)/i.test(clean)) return "thunderstorm";
  if (/(rain|drizzle|shower|雨|陣雨|阵雨|snow|雪|sleet|凍雨|冻雨)/i.test(clean)) return "light_rain";
  if (/(clear|sun|晴)/i.test(clean)) return "sunny";
  if (/(cloud|overcast|mist|fog|haze|smoke|dust|sand|陰|阴|雲|云|霧|雾|霾|沙|塵|尘)/i.test(clean)) return "cloudy";
  return DEFAULT_WEATHER;
}

function normalizePeriod(value) {
  const clean = String(value || DEFAULT_PERIOD).trim().toLowerCase();
  if (/^all[ _-]?day$/.test(clean)) return "all_day";
  if (/sunrise|sunraise|dawn|日出/.test(clean)) return "sunrise";
  if (/morning|早上|上午|晨/.test(clean)) return "morning";
  if (/noon|afternoon|中午|下午/.test(clean)) return "afternoon";
  if (/sunset|dusk|evening|傍晚|黃昏|黄昏/.test(clean)) return "sunset";
  if (/midnight|late|深夜|午夜/.test(clean)) return "midnight";
  if (/night|晚上|夜/.test(clean)) return "night";
  return DEFAULT_PERIOD;
}

function normalizeCharacter(value) {
  const clean = String(value || DEFAULT_CHARACTER).trim().toLowerCase().replace(/[\s-]+/g, "_");
  return CHARACTER_ALIASES[clean] || DEFAULT_CHARACTER;
}

function normalizeStyle(value) {
  const clean = String(value || DEFAULT_STYLE).trim().toLowerCase().replace(/[\s-]+/g, "_");
  return STYLE_ALIASES[clean] || DEFAULT_STYLE;
}

function detectFestival(date) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Taipei",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  const md = `${values.month}-${values.day}`;
  const festivals = {
    "01-01": "new_year",
    "02-14": "valentines_day",
    "10-10": "national_day",
    "10-31": "halloween",
    "12-25": "constitution_day"
  };
  return festivals[md] || "none";
}

function isWeatherRequest(url) {
  return url.searchParams.has("lat") && url.searchParams.has("lon") && !hasAny(url, ["loc", "city"]);
}

function isWallpaperRequest(url) {
  return hasAny(url, ["loc", "city", "cityLocal", "weather", "period", "char", "character", "style"]);
}

function hasAny(url, names) {
  return names.some((name) => url.searchParams.has(name));
}

function firstParam(url, names) {
  for (const name of names) {
    const value = url.searchParams.get(name);
    if (value && value.trim()) return value.trim();
  }
  return "";
}

function safeSceneFromUrl(url) {
  try {
    return parseClientScene(url);
  } catch {
    return {};
  }
}

function parseAdminScene(form) {
  const date = new Date(String(form.get("date") || ""));
  const festivalDate = Number.isNaN(date.getTime()) ? new Date() : date;
  const scene = {
    city: normalizeCity(form.get("city") || form.get("cityLocal") || form.get("loc") || DEFAULT_CITY),
    weather: normalizeWeather(form.get("weather") || DEFAULT_WEATHER),
    period: normalizePeriod(form.get("period") || DEFAULT_PERIOD),
    character: normalizeCharacter(form.get("character") || form.get("char") || DEFAULT_CHARACTER),
    style: normalizeStyle(form.get("style") || DEFAULT_STYLE),
    festival: normalizeFestival(form.get("festival")) || detectFestival(festivalDate)
  };
  scene.period = wallpaperPeriod(scene);
  return scene;
}

function normalizeFestival(value) {
  const clean = String(value || "").trim().toLowerCase();
  if (!clean) return "";
  if (clean === "none" || clean === "no" || clean === "null") return "none";
  return filenamePart(clean);
}

function assertBinding(binding, name) {
  if (!binding) throw new Error(`${name} binding is not configured`);
}

function fileUrl(url, objectKey) {
  return `${url.origin}/files/${encodeURIComponent(objectKey)}`;
}

function filenamePart(value) {
  return String(value || "")
    .trim()
    .replace(/[\\/:*?"<>|]+/g, "")
    .replace(/\s+/g, "")
    .replace(/_+/g, "_")
    .slice(0, 80) || "unknown";
}

function hasPngSignature(buffer) {
  const bytes = new Uint8Array(buffer);
  const signature = [137, 80, 78, 71, 13, 10, 26, 10];
  return bytes.length >= signature.length && signature.every((value, index) => bytes[index] === value);
}

async function timingSafeEqual(left, right) {
  const encoder = new TextEncoder();
  const [leftHash, rightHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(left)),
    crypto.subtle.digest("SHA-256", encoder.encode(right))
  ]);
  const leftBytes = new Uint8Array(leftHash);
  const rightBytes = new Uint8Array(rightHash);
  let result = 0;
  for (let i = 0; i < leftBytes.length; i += 1) {
    result |= leftBytes[i] ^ rightBytes[i];
  }
  return result === 0;
}

function escapeTelegram(value) {
  return String(value || "").replace(/[_*[\]()~`>#+\-=|{}.!]/g, "\\$&");
}

function notModified(reason) {
  return new Response(null, {
    status: 304,
    headers: {
      "cache-control": "no-store",
      "x-wallpaper-status": reason
    }
  });
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
      "access-control-allow-methods": "GET, POST, OPTIONS",
      "access-control-allow-headers": "content-type, authorization"
    }
  });
}
