package com.codex.amigurumiweather;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * QA-mode rules for the admin flavor only. The batch target list is not computed
 * here: it is read from the asset written by tools/worker-wallpaper-audit.mjs
 * --write-manifest, so the App and the Linux audit script share one enumeration.
 */
final class WallpaperQaRules {
    static final String MANIFEST_ASSET = "wallpaper_audit_targets.csv";
    static final String[] MANIFEST_FIELDS = {"kind", "city", "festival", "period", "weather"};
    static final String[] REPORT_FIELDS = {
        "priority", "kind", "city", "festival", "period", "weather", "key",
        "result", "status", "ms", "bytes", "width", "height", "error"
    };
    static final String STYLE = "knitted";
    static final String CHARACTER = "person";
    static final String[] CITIES = {
        "Taipei", "NewTaipei", "Keelung", "Taoyuan", "HsinchuCity", "HsinchuCounty",
        "Miaoli", "Taichung", "Changhua", "Nantou", "Yunlin",
        "ChiayiCity", "ChiayiCounty", "Tainan", "Kaohsiung", "Pingtung",
        "Yilan", "Hualien", "Taitung",
        "Penghu", "Kinmen", "Lienchiang"
    };
    static final String[] FESTIVALS = {
        "none", "new_year", "valentines_day", "national_day", "halloween", "constitution_day"
    };
    static final String[] PERIODS = {"sunrise", "morning", "afternoon", "sunset", "night", "midnight"};
    static final String[] WEATHERS = {
        "sunny", "partly_cloudy", "cloudy", "overcast", "light_rain", "heavy_rain",
        "typhoon", "fog", "haze", "strong_wind", "thunder_shower", "thunderstorm",
        "heatwave", "cold_wave"
    };
    private static final byte[] PNG_SIGNATURE = {(byte) 137, 80, 78, 71, 13, 10, 26, 10};

    private WallpaperQaRules() {
    }

    static final class Target {
        final String priority;
        final String kind;
        final String city;
        final String festival;
        final String period;
        final String weather;
        final String key;

        Target(int priority, String[] cells) {
            this.priority = String.valueOf(priority);
            kind = cells[0];
            city = cells[1];
            festival = cells[2];
            period = cells[3];
            weather = cells[4];
            key = key(festival, city, period, weather);
        }
    }

    static final class Probe {
        String result = "error";
        int status;
        long ms;
        long bytes;
        int width;
        int height;
        String error = "";
        byte[] body;
    }

    /** Mirror of buildWallpaperKey()/wallpaperPeriod() in the Worker. */
    static String key(String festival, String city, String period, String weather) {
        boolean timed = "sunny".equals(weather) || "partly_cloudy".equals(weather);
        String slot = timed ? period : "all_day";
        return "wallpaper/" + STYLE + "/" + CHARACTER + "/"
            + festival + "_" + city + "_" + CHARACTER + "_" + slot + "_" + weather + ".png";
    }

    static List<Target> readManifest(InputStream input) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(input, StandardCharsets.UTF_8));
        String header = reader.readLine();
        if (header == null || !Arrays.equals(header.split(",", -1), MANIFEST_FIELDS)) {
            throw new IllegalStateException("Unexpected manifest header: " + header);
        }
        List<Target> targets = new ArrayList<>();
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.isEmpty()) continue;
            String[] cells = line.split(",", -1);
            if (cells.length != MANIFEST_FIELDS.length) {
                throw new IllegalStateException("Bad manifest row: " + line);
            }
            targets.add(new Target(targets.size() + 1, cells));
        }
        return targets;
    }

    static Target find(List<Target> targets, String key) {
        for (Target target : targets) {
            if (target.key.equals(key)) return target;
        }
        return null;
    }

    /** Same URL shape as fileUrl() in the Worker: /files/ + encodeURIComponent(key). */
    static String fileUrl(String baseUrl, String key) throws Exception {
        String base = baseUrl.trim();
        while (base.endsWith("/")) base = base.substring(0, base.length() - 1);
        return base + "/files/" + URLEncoder.encode(key, "UTF-8").replace("+", "%20");
    }

    /** Width and height from the PNG IHDR chunk, or null if the header is not a PNG. */
    static int[] pngSize(byte[] header, int length) {
        if (length < 24) return null;
        for (int i = 0; i < PNG_SIGNATURE.length; i++) {
            if (header[i] != PNG_SIGNATURE[i]) return null;
        }
        if (header[12] != 'I' || header[13] != 'H' || header[14] != 'D' || header[15] != 'R') return null;
        return new int[] {readInt(header, 16), readInt(header, 20)};
    }

    private static int readInt(byte[] bytes, int offset) {
        return ((bytes[offset] & 0xff) << 24) | ((bytes[offset + 1] & 0xff) << 16)
            | ((bytes[offset + 2] & 0xff) << 8) | (bytes[offset + 3] & 0xff);
    }

    /**
     * GETs one key from the Worker. 200 + PNG header = hit, 404/304 = missing.
     * keepBody keeps the bytes for on-screen preview; batch mode only counts them.
     */
    static Probe probe(String baseUrl, String key, boolean keepBody) {
        Probe probe = new Probe();
        long started = System.nanoTime();
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(fileUrl(baseUrl, key)).openConnection();
            connection.setConnectTimeout(30000);
            connection.setReadTimeout(120000);
            connection.setUseCaches(false);
            probe.status = connection.getResponseCode();
            if (probe.status == 200) {
                byte[] header = new byte[24];
                int headerLength = 0;
                java.io.ByteArrayOutputStream kept = keepBody ? new java.io.ByteArrayOutputStream() : null;
                try (InputStream input = connection.getInputStream()) {
                    byte[] buffer = new byte[64 * 1024];
                    int read;
                    while ((read = input.read(buffer)) != -1) {
                        int copy = Math.min(read, header.length - headerLength);
                        if (copy > 0) {
                            System.arraycopy(buffer, 0, header, headerLength, copy);
                            headerLength += copy;
                        }
                        probe.bytes += read;
                        if (kept != null) kept.write(buffer, 0, read);
                    }
                }
                if (kept != null) probe.body = kept.toByteArray();
                int[] size = pngSize(header, headerLength);
                if (size != null) {
                    probe.result = "hit";
                    probe.width = size[0];
                    probe.height = size[1];
                } else {
                    probe.result = "invalid_png";
                    probe.error = "200 response is not a PNG";
                }
            } else if (probe.status == 404 || probe.status == 304) {
                probe.result = "missing";
            } else {
                probe.error = "unexpected HTTP " + probe.status;
            }
        } catch (Exception error) {
            probe.error = error.getClass().getSimpleName() + ": " + error.getMessage();
        } finally {
            if (connection != null) connection.disconnect();
            probe.ms = Math.round((System.nanoTime() - started) / 1_000_000.0);
        }
        return probe;
    }

    static String csvHeader() {
        return String.join(",", REPORT_FIELDS) + "\n";
    }

    static String csvRow(Target target, Probe probe) {
        String[] cells = {
            target.priority, target.kind, target.city, target.festival, target.period, target.weather, target.key,
            probe.result, probe.status == 0 ? "" : String.valueOf(probe.status), String.valueOf(probe.ms),
            probe.status == 0 ? "" : String.valueOf(probe.bytes),
            probe.width == 0 ? "" : String.valueOf(probe.width),
            probe.height == 0 ? "" : String.valueOf(probe.height),
            probe.error
        };
        StringBuilder row = new StringBuilder();
        for (int i = 0; i < cells.length; i++) {
            if (i > 0) row.append(',');
            row.append(csvCell(cells[i]));
        }
        return row.append('\n').toString();
    }

    static String csvCell(String value) {
        String text = value == null ? "" : value;
        if (text.indexOf(',') < 0 && text.indexOf('"') < 0 && text.indexOf('\n') < 0 && text.indexOf('\r') < 0) {
            return text;
        }
        return '"' + text.replace("\"", "\"\"") + '"';
    }
}
