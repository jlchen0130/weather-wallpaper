#!/usr/bin/env node
// Audit every expected wallpaper key against the deployed Cloudflare Worker.
//
// Read-only: requests GET <base>/files/<encodeURIComponent(key)> (the same URL the
// Worker returns as image_url). That is an exact R2 lookup with no festival or
// legacy fallback: 200 = PNG exists, 404 = missing.
//
// The enumeration here is the single source of truth. The admin App reads the
// manifest written by --write-manifest (app/src/admin/assets), and
// worker-wallpaper-audit.test.mjs fails when that manifest is stale.
//
// Node >= 18, no dependencies.
//   node tools/worker-wallpaper-audit.mjs --out report.csv --summary-json summary.json
//   node tools/worker-wallpaper-audit.mjs --write-manifest .
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

export const DEFAULT_BASE_URL = "https://amigurumi-weather-theme-server.wemmei0130.workers.dev";
export const STYLE = "knitted";
export const CHARACTER = "person";
export const CITIES = [
  "Taipei", "NewTaipei", "Keelung", "Taoyuan", "HsinchuCity", "HsinchuCounty",
  "Miaoli", "Taichung", "Changhua", "Nantou", "Yunlin",
  "ChiayiCity", "ChiayiCounty", "Tainan", "Kaohsiung", "Pingtung",
  "Yilan", "Hualien", "Taitung",
  "Penghu", "Kinmen", "Lienchiang"
];
export const FESTIVALS = ["new_year", "valentines_day", "national_day", "halloween", "constitution_day"];
export const PERIODS = ["sunrise", "morning", "afternoon", "sunset", "night", "midnight"];
export const REGULAR_WEATHERS = ["sunny", "partly_cloudy"];
export const ORDINARY_ALL_DAY_WEATHERS = ["cloudy", "overcast", "light_rain"];
export const ADVERSE_WEATHERS = [
  "heavy_rain", "typhoon", "fog", "haze", "strong_wind",
  "thunder_shower", "thunderstorm", "heatwave", "cold_wave"
];
export const NONE_ALL_DAY_WEATHERS = [...ORDINARY_ALL_DAY_WEATHERS, ...ADVERSE_WEATHERS];
export const MANIFEST_RELATIVE = "app/src/admin/assets/wallpaper_audit_targets.csv";
// The App derives priority (row order) and key (WallpaperQaRules.key) from these columns.
export const MANIFEST_FIELDS = ["kind", "city", "festival", "period", "weather"];
export const REPORT_FIELDS = ["priority", ...MANIFEST_FIELDS, "key",
  "result", "status", "ms", "bytes", "width", "height", "error"];

const HERE = dirname(fileURLToPath(import.meta.url));
export const ELIGIBILITY_FILE = join(HERE, "festival_weather_eligibility.json");
const PNG_SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10];

// Mirror of buildWallpaperKey()/wallpaperPeriod() in the Worker.
export function wallpaperKey(festival, city, period, weather, style = STYLE, character = CHARACTER) {
  const slot = style === "knitted" && character === "person" && !REGULAR_WEATHERS.includes(weather)
    ? "all_day" : period;
  return `wallpaper/${style}/${character}/${festival}_${city}_${character}_${slot}_${weather}.png`;
}

export function loadEligibility(path = ELIGIBILITY_FILE) {
  return JSON.parse(readFileSync(path, "utf8"));
}

// Adverse weathers Codex qualified for this city/festival, in canonical order.
export function festivalAdverse(eligibility, city, festival) {
  const adverse = eligibility?.cities?.[city]?.festivals?.[festival]?.eligible_adverse || [];
  const unknown = adverse.filter((weather) => !ADVERSE_WEATHERS.includes(weather));
  if (unknown.length) throw new Error(`Unknown adverse weather for ${city}/${festival}: ${unknown.join(", ")}`);
  return ADVERSE_WEATHERS.filter((weather) => adverse.includes(weather));
}

// Festival combinations first (plan: 節慶組合優先), then ordinary weather.
export function enumerateTargets(eligibility) {
  const targets = [];
  const add = (kind, city, festival, period, weather) => {
    const key = wallpaperKey(festival, city, period, weather);
    const slot = key.includes("_all_day_") ? "all_day" : period;
    targets.push({ priority: targets.length + 1, kind, city, festival, period: slot, weather, key });
  };
  for (const festival of FESTIVALS) {
    for (const city of CITIES) {
      for (const weather of REGULAR_WEATHERS) {
        for (const period of PERIODS) add("festival", city, festival, period, weather);
      }
      for (const weather of ORDINARY_ALL_DAY_WEATHERS) add("festival", city, festival, "all_day", weather);
      for (const weather of festivalAdverse(eligibility, city, festival)) {
        add("festival_adverse", city, festival, "all_day", weather);
      }
    }
  }
  for (const city of CITIES) {
    for (const weather of REGULAR_WEATHERS) {
      for (const period of PERIODS) add("weather", city, "none", period, weather);
    }
    for (const weather of NONE_ALL_DAY_WEATHERS) add("weather", city, "none", "all_day", weather);
  }
  return targets;
}

export function csvCell(value) {
  const text = value === undefined || value === null ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function toCsv(rows, fields) {
  return [fields.join(","), ...rows.map((row) => fields.map((field) => csvCell(row[field])).join(","))]
    .join("\n") + "\n";
}

export function manifestText(targets) {
  return toCsv(targets, MANIFEST_FIELDS);
}

// Same encoding as fileUrl() in the Worker.
export function fileUrl(baseUrl, key) {
  return `${baseUrl.replace(/\/+$/, "")}/files/${encodeURIComponent(key)}`;
}

// Width/height from the PNG IHDR chunk, or null if this is not a PNG.
export function pngSize(header) {
  if (!header || header.length < 24) return null;
  if (!PNG_SIGNATURE.every((value, index) => header[index] === value)) return null;
  if (String.fromCharCode(...header.subarray(12, 16)) !== "IHDR") return null;
  const view = new DataView(header.buffer, header.byteOffset, header.byteLength);
  return [view.getUint32(16), view.getUint32(20)];
}

export async function probe(target, baseUrl, { timeoutMs = 60000, method = "GET" } = {}) {
  const row = { ...target, result: "error", status: "", ms: "", bytes: "", width: "", height: "", error: "" };
  const started = performance.now();
  try {
    const response = await fetch(fileUrl(baseUrl, target.key), {
      method,
      headers: { "user-agent": "wallpaper-qa-audit/1.0" },
      signal: AbortSignal.timeout(timeoutMs)
    });
    let size = 0;
    let header = new Uint8Array(0);
    if (method === "HEAD") {
      size = Number(response.headers.get("content-length") || 0);
    } else if (response.body) {
      for await (const chunk of response.body) {
        if (header.length < 24) header = concat(header, chunk.subarray(0, 24 - header.length));
        size += chunk.length;
      }
    }
    row.status = String(response.status);
    row.bytes = String(response.status === 200 ? size : 0);
    if (response.status === 200) {
      const dimensions = pngSize(header);
      if (method === "HEAD") {
        row.result = "hit";
      } else if (dimensions) {
        Object.assign(row, { result: "hit", width: String(dimensions[0]), height: String(dimensions[1]) });
      } else {
        Object.assign(row, { result: "invalid_png", error: "200 response is not a PNG" });
      }
    } else if (response.status === 404 || response.status === 304) {
      row.result = "missing";
    } else {
      row.error = `unexpected HTTP ${response.status}`;
    }
  } catch (error) {
    row.error = String(error?.cause?.code || error?.name || "") + ": " + (error?.cause?.message || error?.message || error);
  }
  row.ms = String(Math.round(performance.now() - started));
  return row;
}

function concat(left, right) {
  const out = new Uint8Array(left.length + right.length);
  out.set(left);
  out.set(right, left.length);
  return out;
}

export async function runAudit(targets, baseUrl, { concurrency = 4, timeoutMs = 60000, method = "GET",
  onProgress } = {}) {
  const rows = new Array(targets.length);
  let next = 0;
  let done = 0;
  const lane = async () => {
    while (next < targets.length) {
      const index = next++;
      rows[index] = await probe(targets[index], baseUrl, { timeoutMs, method });
      done += 1;
      onProgress?.(done, targets.length, rows[index]);
    }
  };
  await Promise.all(Array.from({ length: Math.max(1, concurrency) }, lane));
  return rows;
}

export function summarize(rows) {
  const bucket = () => ({ expected: 0, hit: 0, missing: 0, error: 0, hit_rate: 0, missing_keys: [] });
  const overall = bucket();
  const byCity = Object.fromEntries(CITIES.map((city) => [city, bucket()]));
  const byFestival = Object.fromEntries(["none", ...FESTIVALS].map((name) => [name, bucket()]));
  for (const row of rows) {
    for (const group of [overall, byCity[row.city] ??= bucket(), byFestival[row.festival] ??= bucket()]) {
      group.expected += 1;
      if (row.result === "hit") group.hit += 1;
      else {
        if (row.result === "missing") group.missing += 1;
        else group.error += 1;
        group.missing_keys.push(row.key);
      }
    }
  }
  const finish = (groups) => Object.fromEntries(Object.entries(groups)
    .filter(([, group]) => group.expected)
    .map(([name, group]) => [name, { ...group, hit_rate: round(group.hit / group.expected) }]));
  return {
    overall: { ...overall, hit_rate: overall.expected ? round(overall.hit / overall.expected) : 0 },
    by_city: finish(byCity),
    by_festival: finish(byFestival)
  };
}

function round(value) {
  return Math.round(value * 10000) / 10000;
}

export function summaryText(summary, baseUrl) {
  const line = (name, group) => `  ${name.padEnd(17)} ${String(group.hit).padStart(5)}/${String(group.expected).padEnd(5)}`
    + ` missing ${String(group.missing).padEnd(5)} error ${group.error}`;
  const { overall } = summary;
  const lines = [
    `Worker: ${baseUrl}`,
    `Total: ${overall.hit}/${overall.expected} hit (${(overall.hit_rate * 100).toFixed(1)}%), `
      + `missing ${overall.missing}, error ${overall.error}`,
    "",
    "By festival:",
    ...Object.entries(summary.by_festival).map(([name, group]) => line(name, group)),
    "",
    "By city:",
    ...Object.entries(summary.by_city).map(([name, group]) => line(name, group)),
    "",
    "Missing or failed keys by city:"
  ];
  for (const [name, group] of Object.entries(summary.by_city)) {
    if (!group.missing_keys.length) continue;
    lines.push(`  ${name} (${group.missing_keys.length}):`, ...group.missing_keys.map((key) => `    ${key}`));
  }
  return lines.join("\n") + "\n";
}

export function selectTargets(targets, { cities = [], festivals = [], limit = 0 } = {}) {
  const chosen = targets.filter((target) => (!cities.length || cities.includes(target.city))
    && (!festivals.length || festivals.includes(target.festival)));
  return limit > 0 ? chosen.slice(0, limit) : chosen;
}

const USAGE = `Usage: node tools/worker-wallpaper-audit.mjs [options]
  --base-url URL         Worker origin (default: $WALLPAPER_WORKER_URL or ${DEFAULT_BASE_URL})
  --out FILE             CSV report (default: wallpaper_audit_<time>.csv)
  --summary-json FILE    also write the summary as JSON
  --city NAME            repeatable; restrict to these cities
  --festival NAME        repeatable; none|${FESTIVALS.join("|")}
  --limit N              only audit the first N targets
  --concurrency N        parallel requests (default 4)
  --timeout SECONDS      per request (default 60)
  --method GET|HEAD      HEAD skips the download but cannot verify PNG bytes/size
  --list                 print the target manifest and exit (no network)
  --write-manifest ROOT  write ROOT/${MANIFEST_RELATIVE} for the admin App and exit
  --eligibility FILE     festival eligibility JSON (default: tools/festival_weather_eligibility.json)
  --fail-on-missing      exit 1 when any key is missing
Exit codes: 0 ok, 1 missing keys with --fail-on-missing, 2 request errors or invalid PNGs, 64 bad usage.`;

export async function main(argv = process.argv.slice(2), io = { stdout: process.stdout, stderr: process.stderr }) {
  let options;
  try {
    ({ values: options } = parseArgs({
      args: argv,
      options: {
        "base-url": { type: "string", default: process.env.WALLPAPER_WORKER_URL || DEFAULT_BASE_URL },
        out: { type: "string" },
        "summary-json": { type: "string" },
        city: { type: "string", multiple: true, default: [] },
        festival: { type: "string", multiple: true, default: [] },
        limit: { type: "string", default: "0" },
        concurrency: { type: "string", default: "4" },
        timeout: { type: "string", default: "60" },
        method: { type: "string", default: "GET" },
        list: { type: "boolean", default: false },
        "write-manifest": { type: "string" },
        eligibility: { type: "string", default: ELIGIBILITY_FILE },
        "fail-on-missing": { type: "boolean", default: false },
        help: { type: "boolean", default: false }
      }
    }));
    const badCity = options.city.find((city) => !CITIES.includes(city));
    const badFestival = options.festival.find((name) => !["none", ...FESTIVALS].includes(name));
    if (badCity || badFestival) throw new Error(`unknown ${badCity ? `city ${badCity}` : `festival ${badFestival}`}`);
    if (!["GET", "HEAD"].includes(options.method)) throw new Error("--method must be GET or HEAD");
  } catch (error) {
    io.stderr.write(`${error.message}\n${USAGE}\n`);
    return 64;
  }
  if (options.help) {
    io.stdout.write(`${USAGE}\n`);
    return 0;
  }

  const all = enumerateTargets(loadEligibility(options.eligibility));
  if (options["write-manifest"]) {
    const path = resolve(options["write-manifest"], MANIFEST_RELATIVE);
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, manifestText(all));
    io.stdout.write(`wrote ${all.length} targets to ${path}\n`);
    return 0;
  }
  const targets = selectTargets(all, {
    cities: options.city, festivals: options.festival, limit: Number(options.limit) || 0
  });
  if (options.list) {
    io.stdout.write(manifestText(targets));
    return 0;
  }

  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace("T", "-").slice(0, 15);
  const out = options.out || `wallpaper_audit_${stamp}.csv`;
  const baseUrl = options["base-url"];
  const rows = await runAudit(targets, baseUrl, {
    concurrency: Number(options.concurrency) || 4,
    timeoutMs: (Number(options.timeout) || 60) * 1000,
    method: options.method,
    onProgress(done, total, row) {
      if (done % 100 === 0 || done === total || row.result === "error") {
        io.stderr.write(`[${done}/${total}] ${row.result} ${row.status} ${row.key} ${row.error}\n`);
      }
    }
  });
  mkdirSync(dirname(resolve(out)), { recursive: true });
  writeFileSync(out, toCsv(rows, REPORT_FIELDS));
  const summary = summarize(rows);
  if (options["summary-json"]) {
    mkdirSync(dirname(resolve(options["summary-json"])), { recursive: true });
    writeFileSync(options["summary-json"], JSON.stringify(summary, null, 2) + "\n");
  }
  io.stdout.write(summaryText(summary, baseUrl));
  io.stdout.write(`CSV report: ${out}\n`);
  if (summary.overall.error) return 2;
  if (options["fail-on-missing"] && summary.overall.missing) return 1;
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
