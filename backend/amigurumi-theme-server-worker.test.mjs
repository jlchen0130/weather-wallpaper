import assert from "node:assert/strict";
import test from "node:test";

import worker from "./amigurumi-theme-server-worker.js";

class MemoryR2 {
  constructor() {
    this.objects = new Map();
    this.headKeys = [];
    this.putKeys = [];
  }

  async get(key) {
    return this.objects.get(key) || null;
  }

  async head(key) {
    this.headKeys.push(key);
    return this.objects.get(key) || null;
  }

  async put(key, value, options = {}) {
    this.putKeys.push(key);
    this.objects.set(key, {
      body: value,
      httpMetadata: options.httpMetadata || {},
      customMetadata: options.customMetadata || {}
    });
  }
}

function testEnv(bucket = new MemoryR2()) {
  return {
    WALLPAPER_BUCKET: bucket,
    MANUAL_UPLOAD_TOKEN: "local-test-token"
  };
}

function executionContext() {
  const promises = [];
  return {
    promises,
    waitUntil(promise) {
      promises.push(promise);
    }
  };
}

test("R2 miss keeps the current wallpaper without generating a replacement", async () => {
  const bucket = new MemoryR2();
  const response = await worker.fetch(
    new Request("https://example.test/?city=Kaohsiung&weather=Sunny&period=Morning&character=cat&style=knitted"),
    testEnv(bucket),
    executionContext()
  );

  assert.equal(response.status, 304);
  assert.equal(response.headers.get("x-wallpaper-status"), "manual_wallpaper_missing_keep_current_wallpaper");
  assert.deepEqual(bucket.putKeys, []);
});

test("admin upload accepts a valid PNG and writes only a .png key", async () => {
  const bucket = new MemoryR2();
  const form = new FormData();
  form.set("token", "local-test-token");
  form.set("city", "Kaohsiung");
  form.set("weather", "Sunny");
  form.set("period", "Sunrise");
  form.set("character", "cat");
  form.set("style", "knitted");
  form.set("festival", "none");
  form.set("image", new Blob([
    new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 0])
  ], { type: "image/png" }), "wallpaper.png");

  const response = await worker.fetch(
    new Request("https://example.test/admin/upload", { method: "POST", body: form }),
    testEnv(bucket),
    executionContext()
  );
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(body.content_type, "image/png");
  assert.equal(body.asset_kind, "manual_png");
  assert.equal(body.object_key, "wallpaper/knitted/cat/none_Kaohsiung_cat_sunrise_sunny.png");
  assert.deepEqual(bucket.putKeys, [body.object_key]);
});

test("admin upload rejects non-PNG content", async () => {
  const form = new FormData();
  form.set("token", "local-test-token");
  form.set("image", new Blob(["not a png"], { type: "image/jpeg" }), "wallpaper.jpg");

  const response = await worker.fetch(
    new Request("https://example.test/admin/upload", { method: "POST", body: form }),
    testEnv(),
    executionContext()
  );

  assert.equal(response.status, 415);
  assert.deepEqual(await response.json(), { error: "Only image/png uploads are accepted" });
});

test("admin upload rejects invalid bytes disguised as PNG", async () => {
  const bucket = new MemoryR2();
  const form = new FormData();
  form.set("token", "local-test-token");
  form.set("image", new Blob(["not a png"], { type: "image/png" }), "wallpaper.png");

  const response = await worker.fetch(
    new Request("https://example.test/admin/upload", { method: "POST", body: form }),
    testEnv(bucket),
    executionContext()
  );

  assert.equal(response.status, 415);
  assert.deepEqual(await response.json(), { error: "Uploaded file is not a valid PNG" });
  assert.deepEqual(bucket.putKeys, []);
});

test("admin upload rejects oversized requests before multipart parsing", async () => {
  const response = await worker.fetch(
    new Request("https://example.test/admin/upload", {
      method: "POST",
      headers: {
        "content-type": "multipart/form-data; boundary=oversized",
        "content-length": String(13 * 1024 * 1024)
      },
      body: "--oversized--"
    }),
    testEnv(),
    executionContext()
  );

  assert.equal(response.status, 413);
});

test("scheduled audit checks the sunrise PNG slots without creating objects", async () => {
  const bucket = new MemoryR2();
  const ctx = executionContext();
  await worker.scheduled({
    cron: "0 4,9,11,16,21,23 * * *",
    scheduledTime: Date.UTC(2026, 0, 1, 20, 0, 0)
  }, testEnv(bucket), ctx);
  await Promise.all(ctx.promises);

  assert.equal(bucket.headKeys.length, 20);
  assert.ok(bucket.headKeys.every((key) => key.endsWith(
    key.includes("/knitted/person/") ? "_all_day_cloudy.png" : "_sunrise_cloudy.png"
  )));
  assert.deepEqual(bucket.putKeys, []);
});

const canonicalWeathers = [
  "sunny", "partly_cloudy", "cloudy", "overcast", "light_rain", "heavy_rain",
  "typhoon", "fog", "haze", "strong_wind", "thunder_shower", "thunderstorm",
  "heatwave", "cold_wave"
];

for (const weather of canonicalWeathers) {
  test(`upload and lookup preserve the canonical ${weather} filename`, async () => {
    const bucket = new MemoryR2();
    const form = new FormData();
    form.set("token", "local-test-token");
    form.set("city", "HsinchuCounty");
    form.set("weather", weather);
    form.set("period", "morning");
    form.set("festival", "none");
    form.set("image", new Blob([new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10])],
      { type: "image/png" }), "wallpaper.png");
    const upload = await worker.fetch(new Request("https://example.test/admin/upload",
      { method: "POST", body: form }), testEnv(bucket), executionContext());
    const uploaded = await upload.json();
    const period = ["sunny", "partly_cloudy"].includes(weather) ? "morning" : "all_day";
    const expected = `wallpaper/knitted/person/none_HsinchuCounty_person_${period}_${weather}.png`;
    assert.equal(upload.status, 200);
    assert.equal(uploaded.object_key, expected);
    assert.equal(uploaded.period, period);

    // Missing festival variants must fall back to the existing basic asset.
    const response = await worker.fetch(new Request(
      `https://example.test/?city=HsinchuCounty&weather=${weather}&period=morning`),
    testEnv(bucket), executionContext());
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.weather, weather);
    assert.equal(body.period, period);
    assert.ok(body.object_key.endsWith(`_HsinchuCounty_person_${period}_${weather}.png`));
  });
}

test("explicit all_day and distinct city/county aliases survive upload", async () => {
  for (const [city, canonical] of [["新竹市", "HsinchuCity"], ["新竹縣", "HsinchuCounty"],
    ["嘉義市", "ChiayiCity"], ["嘉義縣", "ChiayiCounty"]]) {
    const form = new FormData();
    form.set("token", "local-test-token");
    form.set("city", city);
    form.set("weather", "torrential_rain");
    form.set("period", "all_day");
    form.set("festival", "none");
    form.set("image", new Blob([new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10])],
      { type: "image/png" }), "wallpaper.png");
    const response = await worker.fetch(new Request("https://example.test/admin/upload",
      { method: "POST", body: form }), testEnv(), executionContext());
    assert.equal(response.status, 200);
    assert.equal((await response.json()).object_key,
      `wallpaper/knitted/person/none_${canonical}_person_all_day_heavy_rain.png`);
  }
});

test("festival assets are preferred and basic assets are the fallback", async (t) => {
  const NativeDate = Date;
  class FestivalDate extends NativeDate {
    constructor(...args) {
      super(...(args.length ? args : ["2026-10-10T04:00:00Z"]));
    }
  }
  t.mock.method(globalThis, "Date", FestivalDate);
  const bucket = new MemoryR2();
  const baseKey = "wallpaper/knitted/person/none_Taipei_person_all_day_heavy_rain.png";
  const festivalKey = baseKey.replace("none_", "national_day_");
  bucket.objects.set(baseKey, { body: new Uint8Array() });
  const request = () => new Request("https://example.test/?city=Taipei&weather=heavy_rain&period=night");
  let response = await worker.fetch(request(), testEnv(bucket), executionContext());
  assert.equal((await response.json()).object_key, baseKey);
  bucket.objects.set(festivalKey, { body: new Uint8Array() });
  response = await worker.fetch(request(), testEnv(bucket), executionContext());
  assert.equal((await response.json()).object_key, festivalKey);
});

test("server weather codes select canonical cloudy, rain and thunder categories", async (t) => {
  for (const [id, weather] of [[800, "sunny"], [801, "partly_cloudy"], [803, "cloudy"],
    [804, "overcast"], [500, "light_rain"], [502, "heavy_rain"], [201, "thunder_shower"],
    [211, "thunderstorm"], [741, "fog"], [721, "haze"], [771, "strong_wind"]]) {
    const bucket = new MemoryR2();
    bucket.get = async (key) => {
      assert.ok(key.endsWith(`_${weather}.png`));
      if (!["sunny", "partly_cloudy"].includes(weather)) assert.ok(key.includes("_all_day_"));
      return { body: new Uint8Array() };
    };
    t.mock.method(globalThis, "fetch", async () => Response.json({ weather: [{ id, main: "Clouds" }] }));
    const response = await worker.fetch(new Request(
      "https://example.test/?city=Taipei&weather=sunny&serverWeather=1"),
    { ...testEnv(bucket), OPENWEATHER_API_KEY: "local-test-key" }, executionContext());
    assert.equal(response.status, 200);
    assert.equal((await response.json()).weather, weather);
    t.mock.restoreAll();
  }
});

test("legacy other-character collections remain readable without falling back for knitted people", async () => {
  const bucket = new MemoryR2();
  bucket.objects.set("wallpaper/knitted/cat/none_Hsinchu_cat_morning_rainy.png", { body: new Uint8Array() });
  bucket.objects.set("wallpaper/knitted/person/none_Hsinchu_person_morning_rainy.png", { body: new Uint8Array() });
  const response = await worker.fetch(new Request(
    "https://example.test/?city=HsinchuCity&weather=Rainy&period=morning&character=cat"),
  testEnv(bucket), executionContext());
  assert.equal(response.status, 200);
  assert.equal((await response.json()).object_key,
    "wallpaper/knitted/cat/none_Hsinchu_cat_morning_rainy.png");
  const person = await worker.fetch(new Request(
    "https://example.test/?city=HsinchuCity&weather=Rainy&period=morning&character=person"),
  testEnv(bucket), executionContext());
  assert.equal(person.status, 304);
});
