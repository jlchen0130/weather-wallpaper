import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test, { after, before, describe } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import * as audit from "./worker-wallpaper-audit.mjs";

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
// Unchanged project files (Worker, eligibility JSON, app/src/main). Defaults to this
// checkout; WALLPAPER_BASE_ROOT lets the tests run from a changes-only staging directory.
const BASE_ROOT = process.env.WALLPAPER_BASE_ROOT || REPO_ROOT;
const { default: worker } = await import(
  pathToFileURL(join(BASE_ROOT, "backend", "amigurumi-theme-server-worker.js")).href);
const ELIGIBILITY = join(BASE_ROOT, "tools", "festival_weather_eligibility.json");
const targets = audit.enumerateTargets(audit.loadEligibility(ELIGIBILITY));

function countBy(items, key) {
  const counts = {};
  for (const item of items) counts[key(item)] = (counts[key(item)] || 0) + 1;
  return counts;
}

describe("enumeration rules", () => {
  test("every one of the 22 cities has 24 ordinary weather keys", () => {
    assert.equal(audit.CITIES.length, 22);
    assert.deepEqual(countBy(targets.filter((t) => t.festival === "none"), (t) => t.city),
      Object.fromEntries(audit.CITIES.map((city) => [city, 24])));
  });

  test("every city has the 75 base festival keys, 15 per festival", () => {
    const base = targets.filter((t) => t.kind === "festival");
    assert.deepEqual(countBy(base, (t) => t.city), Object.fromEntries(audit.CITIES.map((city) => [city, 75])));
    assert.deepEqual(new Set(Object.values(countBy(base, (t) => `${t.city}/${t.festival}`))), new Set([15]));
  });

  test("festival totals match the published counts in the plan", () => {
    const counts = countBy(targets.filter((t) => t.festival !== "none"), (t) => t.city);
    const published = { Taipei: 84, NewTaipei: 84, Taoyuan: 82, Taichung: 75, Tainan: 75, Kaohsiung: 75 };
    assert.deepEqual(Object.fromEntries(Object.keys(published).map((city) => [city, counts[city]])), published);
  });

  test("festival combinations come before ordinary weather", () => {
    const firstNone = targets.findIndex((t) => t.festival === "none");
    assert.ok(firstNone > 0);
    assert.ok(targets.slice(0, firstNone).every((t) => t.festival !== "none"));
    assert.ok(targets.slice(firstNone).every((t) => t.festival === "none"));
  });

  test("priorities are sequential and keys unique", () => {
    assert.deepEqual(targets.map((t) => t.priority), targets.map((_, index) => index + 1));
    assert.equal(new Set(targets.map((t) => t.key)).size, targets.length);
  });

  test("only sunny and partly_cloudy have time periods", () => {
    for (const t of targets) {
      if (audit.REGULAR_WEATHERS.includes(t.weather)) assert.ok(audit.PERIODS.includes(t.period), t.key);
      else assert.equal(t.period, "all_day", t.key);
      assert.ok(t.key.endsWith(`/${t.festival}_${t.city}_person_${t.period}_${t.weather}.png`), t.key);
    }
  });

  test("adverse weathers follow the eligibility file in canonical order", () => {
    const eligibility = { cities: { Taipei: { festivals: { halloween: {
      eligible_adverse: ["strong_wind", "typhoon"] } } } } };
    const adverse = audit.enumerateTargets(eligibility).filter((t) => t.kind === "festival_adverse");
    assert.deepEqual(adverse.map((t) => [t.city, t.festival, t.weather]),
      [["Taipei", "halloween", "typhoon"], ["Taipei", "halloween", "strong_wind"]]);
    assert.throws(() => audit.enumerateTargets({ cities: { Taipei: { festivals: { halloween: {
      eligible_adverse: ["snow"] } } } } }), /Unknown adverse weather/);
  });

  test("every enumerated key equals the key the Worker itself builds", async () => {
    // Push every combination through the real Worker's admin upload into a
    // memory bucket and compare the object key it chooses with ours.
    const bucket = { async put() {}, async get() { return null; } };
    const env = { WALLPAPER_BUCKET: bucket, MANUAL_UPLOAD_TOKEN: "local-test-token" };
    for (const t of targets) {
      const form = new FormData();
      form.set("token", "local-test-token");
      for (const field of ["city", "festival", "period", "weather"]) form.set(field, t[field]);
      form.set("style", audit.STYLE);
      form.set("character", audit.CHARACTER);
      form.set("image", new Blob([new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10])], { type: "image/png" }), "x.png");
      const response = await worker.fetch(new Request("https://example.test/admin/upload",
        { method: "POST", body: form }), env, { waitUntil() {} });
      assert.equal((await response.json()).object_key, t.key);
    }
  });

  test("the admin App manifest asset is generated from these rules", () => {
    const path = join(REPO_ROOT, audit.MANIFEST_RELATIVE);
    assert.ok(existsSync(path), `missing ${path}; run node tools/worker-wallpaper-audit.mjs --write-manifest .`);
    assert.equal(readFileSync(path, "utf8"), audit.manifestText(targets),
      "admin App manifest is stale; run node tools/worker-wallpaper-audit.mjs --write-manifest .");
  });
});

describe("helpers", () => {
  test("pngSize reads the IHDR chunk", () => {
    const header = new Uint8Array(24);
    header.set([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82]);
    new DataView(header.buffer).setUint32(16, 1536);
    new DataView(header.buffer).setUint32(20, 2752);
    assert.deepEqual(audit.pngSize(header), [1536, 2752]);
    assert.equal(audit.pngSize(new TextEncoder().encode("not a png at all, definitely")), null);
    assert.equal(audit.pngSize(header.subarray(0, 20)), null);
  });

  test("fileUrl matches the Worker's image_url encoding", () => {
    assert.equal(audit.fileUrl("https://w.test/", "wallpaper/knitted/person/none_Taipei_person_all_day_cloudy.png"),
      "https://w.test/files/wallpaper%2Fknitted%2Fperson%2Fnone_Taipei_person_all_day_cloudy.png");
  });

  test("CSV cells are quoted only when needed", () => {
    assert.equal(audit.toCsv([{ a: "x", b: 'say "hi", ok' }], ["a", "b"]), 'a,b\nx,"say ""hi"", ok"\n');
  });

  test("summary groups by city and festival", () => {
    const summary = audit.summarize([
      { city: "Taipei", festival: "halloween", key: "a", result: "hit" },
      { city: "Taipei", festival: "none", key: "b", result: "missing" },
      { city: "Tainan", festival: "none", key: "c", result: "error" }
    ]);
    assert.equal(summary.overall.expected, 3);
    assert.equal(summary.overall.hit, 1);
    assert.deepEqual(summary.by_city.Taipei.missing_keys, ["b"]);
    assert.deepEqual(summary.by_festival.none.missing_keys, ["b", "c"]);
    assert.equal(summary.by_festival.halloween.hit_rate, 1);
    assert.equal(summary.by_city.Keelung, undefined);
  });

  test("bad arguments exit 64 without touching the network", async () => {
    const io = { stdout: { write() {} }, stderr: { text: "", write(s) { this.text += s; } } };
    assert.equal(await audit.main(["--city", "Tokyo"], io), 64);
    assert.match(io.stderr.text, /unknown city Tokyo/);
  });
});

describe("end to end against the real Worker on 127.0.0.1", () => {
  const taipeiHalloween = targets.filter((t) => t.city === "Taipei" && t.festival === "halloween");
  const present = taipeiHalloween.slice(0, -2).map((t) => t.key);
  const corrupt = taipeiHalloween.at(-2).key;
  const missing = taipeiHalloween.at(-1).key;
  // The "none" fallback object must NOT count as a hit for the festival key.
  const fallbackOnly = missing.replace("/halloween_", "/none_");
  let server;
  let baseUrl;
  let tmp;

  before(async () => {
    const png = new Uint8Array(64);
    png.set([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82]);
    new DataView(png.buffer).setUint32(16, 1536);
    new DataView(png.buffer).setUint32(20, 2752);
    const objects = new Map([...present, fallbackOnly].map((key) => [key, png]));
    objects.set(corrupt, new TextEncoder().encode("not a png"));
    const env = {
      WALLPAPER_BUCKET: {
        async get(key) {
          return objects.has(key) ? { body: objects.get(key), httpMetadata: { contentType: "image/png" } } : null;
        },
        async head(key) { return objects.has(key) ? {} : null; },
        async put() { throw new Error("read-only"); }
      }
    };
    server = createServer(async (req, res) => {
      const response = await worker.fetch(new Request(`http://127.0.0.1${req.url}`, { method: req.method }),
        env, { waitUntil() {} });
      const body = Buffer.from(await response.arrayBuffer());
      res.writeHead(response.status, { ...Object.fromEntries(response.headers), "content-length": body.length });
      res.end(req.method === "HEAD" ? undefined : body);
    });
    await new Promise((done) => server.listen(0, "127.0.0.1", done));
    baseUrl = `http://127.0.0.1:${server.address().port}`;
    tmp = mkdtempSync(join(tmpdir(), "wallpaper-audit-"));
  });

  after(() => {
    server.close();
    rmSync(tmp, { recursive: true, force: true });
  });

  async function runMain(...extra) {
    const out = join(tmp, "report.csv");
    const io = { stdout: { text: "", write(s) { this.text += s; } }, stderr: { write() {} } };
    const code = await audit.main(["--base-url", baseUrl, "--city", "Taipei", "--festival", "halloween",
      "--out", out, "--summary-json", join(tmp, "summary.json"), "--eligibility", ELIGIBILITY, ...extra], io);
    const [header, ...lines] = readFileSync(out, "utf8").trim().split("\n");
    const fields = header.split(",");
    const rows = lines.map((line) => Object.fromEntries(line.split(",").map((cell, i) => [fields[i], cell])));
    return { code, text: io.stdout.text, rows };
  }

  test("GET reports hits with size, misses, and invalid PNG bytes", async () => {
    const { code, text, rows } = await runMain();
    assert.deepEqual(rows.map((row) => row.key), taipeiHalloween.map((t) => t.key));
    assert.equal(rows.length, 18); // 12 timed + 3 ordinary all_day + 3 qualified adverse
    const byKey = Object.fromEntries(rows.map((row) => [row.key, row]));
    for (const key of present) {
      assert.equal(byKey[key].result, "hit");
      assert.equal(byKey[key].status, "200");
      assert.equal(`${byKey[key].width}x${byKey[key].height}`, "1536x2752");
      assert.equal(byKey[key].bytes, "64");
      assert.match(byKey[key].ms, /^\d+$/);
    }
    assert.equal(byKey[corrupt].result, "invalid_png");
    assert.deepEqual([byKey[missing].result, byKey[missing].status], ["missing", "404"]);
    assert.equal(code, 2);
    assert.match(text, /Total: 16\/18 hit/);
    assert.ok(text.includes(missing));
    const summary = JSON.parse(readFileSync(join(tmp, "summary.json"), "utf8"));
    assert.equal(summary.by_festival.halloween.missing, 1);
    assert.equal(summary.by_city.Taipei.error, 1);
  });

  test("HEAD mode and --fail-on-missing", async () => {
    const { code, rows } = await runMain("--method", "HEAD", "--fail-on-missing");
    assert.deepEqual(countBy(rows, (row) => row.result), { hit: 17, missing: 1 });
    assert.equal(code, 1);
  });

  test("an unreachable Worker is reported as error, not as missing", async () => {
    const saved = baseUrl;
    baseUrl = "http://127.0.0.1:9";
    try {
      const { code, rows } = await runMain("--limit", "2", "--timeout", "5");
      assert.deepEqual(rows.map((row) => row.result), ["error", "error"]);
      assert.equal(code, 2);
    } finally {
      baseUrl = saved;
    }
  });
});

describe("admin flavor isolation", () => {
  function files(root) {
    if (!existsSync(root)) return [];
    return readdirSync(root).flatMap((name) => {
      const path = join(root, name);
      return statSync(path).isDirectory() ? files(path) : [path];
    });
  }

  test("QA code is absent from main, universal and galaxyZFold5 source sets", () => {
    const roots = [...new Set([REPO_ROOT, BASE_ROOT])];
    const scanned = roots.flatMap((root) => ["main", "universal", "galaxyZFold5"]
      .flatMap((sourceSet) => files(join(root, "app", "src", sourceSet))));
    assert.ok(scanned.some((path) => path.endsWith("MainActivity.java")), "main source set was not scanned");
    for (const path of scanned) {
      if (!/\.(java|kt|xml|csv)$/.test(path)) continue;
      const text = readFileSync(path, "utf8");
      assert.ok(!text.includes("WallpaperQa"), path);
      assert.ok(!text.includes("wallpaper_audit_targets"), path);
    }
  });

  test("admin source set declares the QA activity and reads the shared manifest", () => {
    const admin = join(REPO_ROOT, "app", "src", "admin");
    assert.match(readFileSync(join(admin, "AndroidManifest.xml"), "utf8"), /android:name="\.WallpaperQaActivity"/);
    const rules = readFileSync(join(admin, "java/com/codex/amigurumiweather/WallpaperQaRules.java"), "utf8");
    assert.ok(rules.includes(`"${audit.MANIFEST_RELATIVE.split("/").at(-1)}"`));
    assert.ok(rules.includes(`{${audit.MANIFEST_FIELDS.map((f) => `"${f}"`).join(", ")}}`));
    const reportFields = rules.match(/REPORT_FIELDS = \{([^}]*)\}/)[1].match(/"[^"]+"/g).map((s) => s.slice(1, -1));
    assert.deepEqual(reportFields, audit.REPORT_FIELDS);
    const javaList = (name) => rules.match(new RegExp(`${name} = \\{([^}]*)\\}`))[1]
      .match(/"[^"]+"/g).map((s) => s.slice(1, -1));
    for (const list of ["CITIES", "PERIODS"]) assert.deepEqual(javaList(list), audit[list], list);
    assert.deepEqual(javaList("FESTIVALS"), ["none", ...audit.FESTIVALS]);
    assert.deepEqual(javaList("WEATHERS"), [...audit.REGULAR_WEATHERS, ...audit.NONE_ALL_DAY_WEATHERS]);
    // Java key() must keep the Worker's rule: only sunny/partly_cloudy keep a time period.
    assert.match(rules, /"sunny"\.equals\(weather\) \|\| "partly_cloudy"\.equals\(weather\)/);
    assert.match(rules, /String slot = timed \? period : "all_day";/);
  });
});
