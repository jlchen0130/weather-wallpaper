const DEFAULT_IMAGE_MODEL = "gpt-image-1";
const IMAGE_SIZE = "1024x1536";
const DEFAULT_STYLE = "knitted";
const DEFAULT_CHARACTER = "person";
const DEFAULT_PERIOD = "afternoon";
const DEFAULT_WEATHER = "cloudy";
const DEFAULT_CITY = "Kaohsiung";
const DEFAULT_DAILY_GENERATION_LIMIT = 8;
const LOCK_TTL_MS = 15 * 60 * 1000;

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
  "新竹市": "Hsinchu",
  "新竹縣": "Hsinchu",
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
  "嘉義市": "Chiayi",
  "嘉義縣": "Chiayi",
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

const LANDMARKS = {
  Kaohsiung: ["85 Sky Tower", "Love River", "Pier-2 Art Center", "Lotus Pond", "Fo Guang Shan Buddha Museum"],
  Taipei: ["Taipei 101", "Dadaocheng", "Raohe Night Market", "Chiang Kai-shek Memorial Hall", "Ximending"],
  NewTaipei: ["Tamsui Old Street", "Jiufen", "Yehliu Geopark", "Shifen Waterfall", "Bitan"],
  Taoyuan: ["Daxi Old Street", "Shimen Reservoir", "Xpark", "Hutoushan Park"],
  Taichung: ["National Taichung Theater", "Miyahara", "Gaomei Wetlands", "Rainbow Village"],
  Tainan: ["Chihkan Tower", "Anping Tree House", "Shennong Street", "Tainan Confucius Temple"],
  Keelung: ["Keelung Harbor", "Miaokou Night Market", "Heping Island Park"],
  Hsinchu: ["Hsinchu City God Temple", "Hsinchu Zoo", "Eighteen Peaks Mountain"],
  Miaoli: ["Shengxing Station", "Longteng Bridge", "Nanzhuang Old Street"],
  Changhua: ["Baguashan Buddha", "Lukang Old Street", "Wangong Fishing Port"],
  Nantou: ["Sun Moon Lake", "Qingjing Farm", "Xitou Nature Education Area"],
  Yunlin: ["Beigang Chaotian Temple", "Gukeng Green Tunnel", "Xiluo Bridge"],
  Chiayi: ["Alishan Forest Railway", "Hinoki Village", "Wenhua Road Night Market"],
  Pingtung: ["Kenting National Park", "Dapeng Bay", "Donggang Huaqiao Market"],
  Yilan: ["Lanyang Museum", "Luodong Night Market", "Dongshan River Water Park"],
  Hualien: ["Taroko Gorge", "Qixingtan", "Dongdamen Night Market"],
  Taitung: ["Taitung Forest Park", "Sanxiantai", "Tiehua Music Village"],
  Penghu: ["Penghu Great Bridge", "Twin Hearts Stone Weir", "Qimei"],
  Kinmen: ["Juguang Tower", "Shuitou Village", "Zhaishan Tunnel"],
  Lienchiang: ["Qinbi Village", "Beihai Tunnel", "Matsu Blue Tears"]
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
      if (isWallpaperRequest(url)) return wallpaperResponse(request, env, ctx);
      return json({
        service: "weather-wallpaper-server",
        compatible_params: ["loc", "city", "cityLocal", "weather", "period", "char", "character", "style"],
        object_key_format: "wallpaper/<style>/<char>/<festival>_<city>_<char>_<period>_<weather>.<ext>"
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
    ctx.waitUntil(Promise.resolve().then(() => {
      console.log(JSON.stringify({
        level: "info",
        event: "scheduled_heartbeat",
        cron: event.cron,
        scheduledTime: event.scheduledTime
      }));
    }));
  }
};

async function wallpaperResponse(request, env, ctx) {
  assertBinding(env.WALLPAPER_BUCKET, "WALLPAPER_BUCKET");
  const url = new URL(request.url);
  const scene = await completeScene(parseClientScene(url), url, env);
  const objectKey = buildWallpaperKey(scene, "png");
  const cached = await env.WALLPAPER_BUCKET.get(objectKey);

  if (cached && isCurrentDailyWallpaper(cached)) {
    return wallpaperJson(url, scene, objectKey, true);
  }

  const lockKey = `locks/${objectKey}.json`;
  const lock = await env.WALLPAPER_BUCKET.get(lockKey);
  if (lock && !isLockExpired(lock.uploaded)) {
    return notModified("generation_already_pending_keep_current_wallpaper");
  }

  const dailyCount = await countDailyGenerations(env, scene);
  const dailyLimit = dailyGenerationLimit(env);
  if (dailyCount >= dailyLimit) {
    waitUntilSafe(ctx, sendTelegramAlert(env, {
      title: "Daily OpenAI generation limit reached",
      error: new Error(`daily generation limit reached: ${dailyLimit}`),
      scene
    }));
    return notModified("daily_generation_limit_keep_current_wallpaper");
  }

  try {
    await env.WALLPAPER_BUCKET.put(lockKey, JSON.stringify({
      objectKey,
      scene,
      createdAt: new Date().toISOString()
    }), {
      httpMetadata: { contentType: "application/json; charset=utf-8" }
    });
    const bytes = await generateWallpaper(env, scene);
    await env.WALLPAPER_BUCKET.put(objectKey, bytes, {
      httpMetadata: { contentType: "image/png" },
      customMetadata: {
        style: scene.style,
        festival: scene.festival,
        character: scene.character,
        city: scene.city,
        period: scene.period,
        weather: scene.weather,
        source: "openai-image-api",
        generatedDate: currentDateKey(),
        generatedAt: new Date().toISOString()
      }
    });
    return wallpaperJson(url, scene, objectKey, false);
  } catch (error) {
    console.log(JSON.stringify({
      level: "error",
      event: "wallpaper_generation_failed",
      message: error?.message || String(error),
      city: scene.city,
      period: scene.period,
      weather: scene.weather,
      character: scene.character,
      style: scene.style
    }));
    waitUntilSafe(ctx, sendTelegramAlert(env, {
      title: "OpenAI wallpaper generation failed",
      error,
      scene
    }));
    return notModified("generation_failed_keep_current_wallpaper");
  } finally {
    await env.WALLPAPER_BUCKET.delete(lockKey);
  }
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

  const form = await request.formData();
  const providedToken = String(form.get("token") || "");
  if (!timingSafeEqual(providedToken, expectedToken)) return json({ error: "Unauthorized" }, 401);

  const image = form.get("image");
  if (!image || typeof image.arrayBuffer !== "function") {
    return json({ error: "Missing image file" }, 400);
  }

  const scene = parseAdminScene(form);
  const contentType = sanitizeContentType(image.type || "image/png");
  const extension = extensionForContentType(contentType);
  const objectKey = buildWallpaperKey(scene, extension);
  const bytes = await image.arrayBuffer();

  await env.WALLPAPER_BUCKET.put(objectKey, bytes, {
    httpMetadata: { contentType },
    customMetadata: {
      style: scene.style,
      festival: scene.festival,
      character: scene.character,
      city: scene.city,
      period: scene.period,
      weather: scene.weather,
      source: "manual-chatgpt-upload",
      generatedDate: currentDateKey(),
      generatedAt: new Date().toISOString()
    }
  });

  return wallpaperJson(new URL(request.url), scene, objectKey, false, contentType, "manual_uploaded");
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
    return normalizeWeather(body?.weather?.[0]?.main || body?.weather?.[0]?.description || "");
  } catch (error) {
    console.log(JSON.stringify({ level: "warn", event: "server_weather_exception", city: scene.city, message: error?.message || String(error) }));
    return "";
  }
}

function currentServerPeriod() {
  const hour = Number(new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Taipei",
    hour: "2-digit",
    hour12: false
  }).format(new Date()));
  if (hour >= 4 && hour <= 6) return "morning";
  if (hour >= 7 && hour <= 15) return "afternoon";
  if (hour >= 16 && hour <= 18) return "sunset";
  if (hour >= 19 && hour <= 22) return "night";
  return "midnight";
}

function buildWallpaperKey(scene, extension = "png") {
  const fileName = [
    scene.festival,
    scene.city,
    scene.character,
    scene.period,
    scene.weather
  ].map(filenamePart).join("_");
  return `wallpaper/${filenamePart(scene.style)}/${filenamePart(scene.character)}/${fileName}.${filenamePart(extension)}`;
}

async function countDailyGenerations(env, scene) {
  const prefix = `wallpaper/${filenamePart(scene.style)}/${filenamePart(scene.character)}/`;
  const listed = await env.WALLPAPER_BUCKET.list({ prefix, limit: 1000 });
  const today = currentDateKey();
  return (listed.objects || []).filter((object) => {
    const metadata = object.customMetadata || {};
    return metadata.source === "openai-image-api"
      && metadata.generatedDate === today
      && metadata.city === scene.city;
  }).length;
}

function isCurrentDailyWallpaper(object) {
  const metadata = object?.customMetadata || {};
  return metadata.generatedDate === currentDateKey();
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

function dailyGenerationLimit(env) {
  const value = Number(env.MAX_DAILY_GENERATIONS_PER_CITY || DEFAULT_DAILY_GENERATION_LIMIT);
  if (!Number.isFinite(value)) return DEFAULT_DAILY_GENERATION_LIMIT;
  return Math.max(1, Math.min(50, Math.floor(value)));
}

function isLockExpired(uploaded) {
  if (!uploaded) return false;
  return Date.now() - new Date(uploaded).getTime() > LOCK_TTL_MS;
}

async function generateWallpaper(env, scene) {
  if (!env.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is not configured");
  const prompt = buildPrompt(scene);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 100000);
  const response = await fetch("https://api.openai.com/v1/images/generations", {
    method: "POST",
    signal: controller.signal,
    headers: {
      authorization: `Bearer ${env.OPENAI_API_KEY}`,
      "content-type": "application/json"
    },
    body: JSON.stringify({
      model: env.OPENAI_IMAGE_MODEL || DEFAULT_IMAGE_MODEL,
      prompt,
      size: IMAGE_SIZE,
      n: 1
    })
  }).finally(() => clearTimeout(timeout));
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = body?.error?.message || `OpenAI HTTP ${response.status}`;
    throw new Error(message);
  }
  const b64 = body?.data?.[0]?.b64_json;
  if (!b64) throw new Error("OpenAI response did not include b64_json");
  return Uint8Array.from(atob(b64), (char) => char.charCodeAt(0));
}

function buildPrompt(scene) {
  const landmarks = LANDMARKS[scene.city] || LANDMARKS[DEFAULT_CITY];
  const stylePrompt = scene.style === "colored_pencil"
    ? "colored pencil illustration, soft paper grain, visible hand-drawn strokes, warm fairy-tale atmosphere, delicate shading"
    : "premium handmade knitted crochet amigurumi style, yarn texture, plush miniature buildings, crochet clouds, stitched details, cozy handcrafted lighting";
  const characterPrompt = {
    person: "Q-version cute people doing ordinary daily life actions such as walking, shopping, chatting, holding drinks, taking photos, and riding a tiny scooter",
    cat: "Q-version cute cats of different breeds doing daily life actions, walking, shopping, chatting, relaxing, and exploring the city",
    dog: "Q-version cute dogs doing daily life actions, walking with bags, playing, greeting friends, and exploring the city",
    hamster_chinchilla: "Q-version hamsters and chinchillas with round bodies doing daily life actions, carrying tiny bags and enjoying the city",
    parrot: "Q-version parrots with bright feathers doing daily life actions, perching, flying gently, shopping, and interacting with the city"
  }[scene.character] || "Q-version cute people doing daily life actions";

  return [
    "Create a vertical 9:16 high-resolution phone live wallpaper background.",
    `Visual style: ${stylePrompt}.`,
    `Scene: ${scene.city}, Taiwan, city-level only. Do not show districts, streets, or townships as the main identity.`,
    `Weather mood: ${scene.weather}. Time period: ${scene.period}. Festival: ${scene.festival}.`,
    `Use 2 to 4 recognizable local landmarks naturally in the distance: ${landmarks.slice(0, 4).join(", ")}.`,
    characterPrompt + ".",
    "Add subtle motion cues suitable for a live wallpaper: drifting clouds, soft light shimmer, rain streaks or lightning glow when weather requires it, walking poses, moving boats or scooters, fluttering fabric, and lively daily activity.",
    "Keep composition calm, premium, cute, and not crowded. Leave the top area clean enough for phone status and clock widgets.",
    "Avoid city-name title text, large labels, phone UI, clock, date, battery, signal icons, app labels, logos, and watermarks."
  ].join("\n");
}

function wallpaperJson(url, scene, objectKey, reused, contentType = "image/png", cache = null) {
  return json({
    file_name: objectKey.split("/").pop(),
    object_key: objectKey,
    image_url: fileUrl(url, objectKey),
    content_type: contentType,
    asset_kind: "generated_image",
    reused,
    cache: cache || (reused ? "hit" : "miss_generated"),
    city: scene.city,
    weather: scene.weather,
    period: scene.period,
    character: scene.character,
    style: scene.style,
    festival: scene.festival,
    animation: {
      type: "server-wallpaper-file",
      format: "mp4-key-compatible-image-payload",
      payload_content_type: "image/png"
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
  const clean = String(value || DEFAULT_WEATHER).trim().toLowerCase();
  if (/(thunder|storm|雷|閃電|闪电|hail|冰雹)/i.test(clean)) return "thunder";
  if (/(rain|drizzle|shower|雨|陣雨|阵雨|豪雨|暴雨|snow|雪|sleet|凍雨|冻雨)/i.test(clean)) return "rainy";
  if (/(clear|sun|晴)/i.test(clean)) return "sunny";
  if (/(cloud|overcast|mist|fog|haze|smoke|dust|sand|陰|阴|雲|云|霧|雾|霾|沙|塵|尘)/i.test(clean)) return "cloudy";
  return DEFAULT_WEATHER;
}

function normalizePeriod(value) {
  const clean = String(value || DEFAULT_PERIOD).trim().toLowerCase();
  if (/sunrise|sunraise|dawn|morning|早|晨/.test(clean)) return "morning";
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
  const md = `${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
  const festivals = {
    "01-01": "new_year",
    "02-14": "valentines_day",
    "10-31": "halloween",
    "12-25": "christmas"
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
  return {
    city: normalizeCity(form.get("city") || form.get("cityLocal") || form.get("loc") || DEFAULT_CITY),
    weather: normalizeWeather(form.get("weather") || DEFAULT_WEATHER),
    period: normalizePeriod(form.get("period") || DEFAULT_PERIOD),
    character: normalizeCharacter(form.get("character") || form.get("char") || DEFAULT_CHARACTER),
    style: normalizeStyle(form.get("style") || DEFAULT_STYLE),
    festival: normalizeFestival(form.get("festival")) || detectFestival(festivalDate)
  };
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

function sanitizeContentType(value) {
  const clean = String(value || "image/png").toLowerCase();
  if (clean.includes("jpeg")) return "image/jpeg";
  if (clean.includes("jpg")) return "image/jpeg";
  if (clean.includes("webp")) return "image/webp";
  if (clean.includes("mp4")) return "video/mp4";
  return "image/png";
}

function extensionForContentType(contentType) {
  if (contentType === "image/jpeg") return "jpg";
  if (contentType === "image/webp") return "webp";
  if (contentType === "video/mp4") return "mp4";
  return "png";
}

function timingSafeEqual(left, right) {
  if (left.length !== right.length) return false;
  let result = 0;
  for (let i = 0; i < left.length; i += 1) {
    result |= left.charCodeAt(i) ^ right.charCodeAt(i);
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
