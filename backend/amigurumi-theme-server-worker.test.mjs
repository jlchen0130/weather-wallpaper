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
  assert.ok(bucket.headKeys.every((key) => key.endsWith("_sunrise_cloudy.png")));
  assert.deepEqual(bucket.putKeys, []);
});
