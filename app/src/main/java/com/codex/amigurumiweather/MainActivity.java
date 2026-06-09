package com.codex.amigurumiweather;

import android.Manifest;
import android.app.Activity;
import android.app.WallpaperManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.location.Address;
import android.location.Geocoder;
import android.location.Location;
import android.location.LocationManager;
import android.os.Bundle;
import android.text.InputType;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;
    private TextView statusText;
    private TextView promptText;
    private ImageView preview;
    private EditText openWeatherKey;
    private EditText openAiKey;
    private EditText openAiModel;
    private EditText customCity;
    private EditText updateMinutes;
    private CheckBox useCustomLocation;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        setContentView(buildUi());
        requestLocationPermissionIfNeeded();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(28));
        root.setBackgroundColor(Color.rgb(255, 248, 239));

        TextView title = new TextView(this);
        title.setText("Amigurumi Weather Theme");
        title.setTextSize(24f);
        title.setTextColor(Color.rgb(65, 45, 34));
        title.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("Static wallpaper plus animated Live Wallpaper. Location can be automatic or custom.");
        subtitle.setTextSize(14f);
        subtitle.setTextColor(Color.rgb(92, 74, 62));
        subtitle.setPadding(0, dp(6), 0, dp(14));
        root.addView(subtitle);

        useCustomLocation = new CheckBox(this);
        useCustomLocation.setText("Use custom city instead of GPS");
        useCustomLocation.setChecked(prefs.getBoolean(AppConfig.KEY_USE_CUSTOM, false));
        root.addView(useCustomLocation);

        customCity = input("Custom city: Kaohsiung / Taipei / Tokyo", AppConfig.KEY_CUSTOM_CITY, false);
        if (customCity.getText().toString().trim().isEmpty()) {
            customCity.setText("Kaohsiung");
        }
        updateMinutes = input("Live update interval minutes", AppConfig.KEY_UPDATE_MINUTES, false);
        if (updateMinutes.getText().toString().trim().isEmpty()) {
            updateMinutes.setText("30");
        }
        openWeatherKey = input("OpenWeather API Key", AppConfig.KEY_OPENWEATHER, true);
        openAiKey = input("OpenAI API Key", AppConfig.KEY_OPENAI, true);
        openAiModel = input("OpenAI image model", AppConfig.KEY_OPENAI_MODEL, false);
        if (openAiModel.getText().toString().trim().isEmpty()) {
            openAiModel.setText("gpt-image-1.5");
        }

        root.addView(customCity);
        root.addView(updateMinutes);
        root.addView(openWeatherKey);
        root.addView(openAiKey);
        root.addView(openAiModel);

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER);
        row.setPadding(0, dp(10), 0, dp(10));

        Button save = new Button(this);
        save.setText("Save");
        save.setOnClickListener(v -> saveSettings());
        LinearLayout.LayoutParams saveParams = new LinearLayout.LayoutParams(0, dp(48), 1f);
        saveParams.setMarginEnd(dp(8));
        row.addView(save, saveParams);

        Button generate = new Button(this);
        generate.setText("Set static wallpaper");
        generate.setOnClickListener(v -> {
            saveSettings();
            generateAndApplyWallpaper();
        });
        row.addView(generate, new LinearLayout.LayoutParams(0, dp(48), 1.4f));
        root.addView(row);

        Button live = new Button(this);
        live.setText("Open animated Live Wallpaper");
        live.setOnClickListener(v -> {
            saveSettings();
            openLiveWallpaperPicker();
        });
        root.addView(live, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(48)));

        statusText = new TextView(this);
        statusText.setText("Status: ready");
        statusText.setTextSize(14f);
        statusText.setTextColor(Color.rgb(65, 45, 34));
        statusText.setPadding(0, dp(12), 0, dp(10));
        root.addView(statusText);

        preview = new ImageView(this);
        preview.setBackgroundColor(Color.rgb(241, 224, 204));
        preview.setAdjustViewBounds(true);
        preview.setScaleType(ImageView.ScaleType.CENTER_CROP);
        root.addView(preview, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(430)));

        promptText = new TextView(this);
        promptText.setTextSize(13f);
        promptText.setTextColor(Color.rgb(65, 45, 34));
        promptText.setPadding(0, dp(16), 0, 0);
        root.addView(promptText);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        return scroll;
    }

    private EditText input(String hint, String key, boolean secret) {
        EditText editText = new EditText(this);
        editText.setHint(hint);
        editText.setSingleLine(true);
        editText.setText(prefs.getString(key, ""));
        editText.setInputType(secret
            ? InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
            : InputType.TYPE_CLASS_TEXT);
        editText.setPadding(dp(12), 0, dp(12), 0);
        return editText;
    }

    private void saveSettings() {
        String model = openAiModel.getText().toString().trim();
        if (model.isEmpty()) model = "gpt-image-1.5";
        int minutes = AppConfig.parseMinutes(updateMinutes.getText().toString());
        prefs.edit()
            .putBoolean(AppConfig.KEY_USE_CUSTOM, useCustomLocation.isChecked())
            .putString(AppConfig.KEY_CUSTOM_CITY, customCity.getText().toString().trim())
            .putString(AppConfig.KEY_UPDATE_MINUTES, Integer.toString(minutes))
            .putString(AppConfig.KEY_OPENWEATHER, openWeatherKey.getText().toString().trim())
            .putString(AppConfig.KEY_OPENAI, openAiKey.getText().toString().trim())
            .putString(AppConfig.KEY_OPENAI_MODEL, model)
            .apply();
        updateMinutes.setText(Integer.toString(minutes));
        Toast.makeText(this, "Saved", Toast.LENGTH_SHORT).show();
    }

    private void requestLocationPermissionIfNeeded() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED
            && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] {
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            }, 100);
        }
    }

    private void generateAndApplyWallpaper() {
        status("Status: building scene...");
        executor.execute(() -> {
            try {
                WeatherScene scene = SceneResolver.resolve(this);
                String prompt = PromptBuilder.build(scene);
                String apiKey = prefs.getString(AppConfig.KEY_OPENAI, "");
                String model = prefs.getString(AppConfig.KEY_OPENAI_MODEL, "gpt-image-1.5");
                Bitmap bitmap = LocalWallpaperRenderer.render(scene);
                WallpaperStore.save(this, bitmap);
                Bitmap previewBitmap = bitmap;
                runOnUiThread(() -> {
                    preview.setImageBitmap(Bitmap.createScaledBitmap(previewBitmap, 360, 640, true));
                    promptText.setText(prompt);
                    statusText.setText("Status: local preview ready. Generating AI image if API key is set...");
                });

                if (apiKey != null && !apiKey.trim().isEmpty()) {
                    Bitmap generated = ImageGenerator.generate(apiKey.trim(), model, prompt);
                    if (generated != null) {
                        bitmap = generated;
                        WallpaperStore.save(this, bitmap);
                    }
                }

                WallpaperManager.getInstance(this).setBitmap(bitmap);
                Bitmap finalBitmap = bitmap;
                runOnUiThread(() -> {
                    preview.setImageBitmap(Bitmap.createScaledBitmap(finalBitmap, 360, 640, true));
                    promptText.setText(prompt);
                    statusText.setText("Status: wallpaper set for " + scene.cityEnglish + ", " + scene.weather + ", " + scene.tempMin + "C~" + scene.tempMax + "C.");
                });
            } catch (Exception error) {
                WeatherScene scene = SceneFactory.createFallback();
                Bitmap bitmap = LocalWallpaperRenderer.render(scene);
                try {
                    WallpaperStore.save(this, bitmap);
                    WallpaperManager.getInstance(this).setBitmap(bitmap);
                } catch (Exception ignored) {
                }
                runOnUiThread(() -> {
                    preview.setImageBitmap(Bitmap.createScaledBitmap(bitmap, 360, 640, true));
                    promptText.setText(PromptBuilder.build(scene));
                    statusText.setText("Status: fallback wallpaper. " + error.getMessage());
                });
            }
        });
    }

    private void openLiveWallpaperPicker() {
        try {
            Intent intent = new Intent(WallpaperManager.ACTION_CHANGE_LIVE_WALLPAPER);
            intent.putExtra(WallpaperManager.EXTRA_LIVE_WALLPAPER_COMPONENT,
                new ComponentName(this, DynamicWallpaperService.class));
            startActivity(intent);
        } catch (Exception error) {
            startActivity(new Intent(WallpaperManager.ACTION_LIVE_WALLPAPER_CHOOSER));
        }
    }

    private void status(String message) {
        runOnUiThread(() -> statusText.setText(message));
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}

class AppConfig {
    static final String PREFS = "theme_config";
    static final String KEY_OPENWEATHER = "openweather_key";
    static final String KEY_OPENAI = "openai_key";
    static final String KEY_OPENAI_MODEL = "openai_model";
    static final String KEY_USE_CUSTOM = "use_custom_location";
    static final String KEY_CUSTOM_CITY = "custom_city";
    static final String KEY_UPDATE_MINUTES = "update_minutes";
    static final String LAST_WALLPAPER_FILE = "last_wallpaper.png";

    static int parseMinutes(String raw) {
        try {
            int minutes = Integer.parseInt(raw.trim());
            if (minutes < 5) return 5;
            if (minutes > 1440) return 1440;
            return minutes;
        } catch (Exception ignored) {
            return 30;
        }
    }
}

class WallpaperStore {
    static void save(Context context, Bitmap bitmap) {
        try {
            File file = new File(context.getFilesDir(), AppConfig.LAST_WALLPAPER_FILE);
            try (FileOutputStream out = new FileOutputStream(file)) {
                bitmap.compress(Bitmap.CompressFormat.PNG, 92, out);
            }
        } catch (Exception ignored) {
        }
    }

    static Bitmap load(Context context) {
        try {
            File file = new File(context.getFilesDir(), AppConfig.LAST_WALLPAPER_FILE);
            if (!file.exists()) return null;
            try (FileInputStream input = new FileInputStream(file)) {
                return BitmapFactory.decodeStream(input);
            }
        } catch (Exception ignored) {
            return null;
        }
    }
}

class SceneResolver {
    static WeatherScene resolve(Context context) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        if (prefs.getBoolean(AppConfig.KEY_USE_CUSTOM, false)) {
            CityInfo city = CityDatabase.forName(prefs.getString(AppConfig.KEY_CUSTOM_CITY, "Kaohsiung"));
            return SceneFactory.create(city, fetchWeather(context, city.latitude, city.longitude));
        }

        Location location = findBestLocation(context);
        CityInfo city = reverseGeocode(context, location);
        return SceneFactory.create(city, fetchWeather(context, location.getLatitude(), location.getLongitude()));
    }

    private static Location findBestLocation(Context context) {
        if (context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED
            && context.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            return CityDatabase.forName("Kaohsiung").toLocation();
        }

        LocationManager manager = (LocationManager) context.getSystemService(Context.LOCATION_SERVICE);
        Location best = null;
        for (String provider : manager.getProviders(true)) {
            try {
                Location candidate = manager.getLastKnownLocation(provider);
                if (candidate != null && (best == null || candidate.getTime() > best.getTime())) {
                    best = candidate;
                }
            } catch (SecurityException ignored) {
            }
        }
        return best != null ? best : CityDatabase.forName("Kaohsiung").toLocation();
    }

    private static CityInfo reverseGeocode(Context context, Location location) {
        Address address = null;
        try {
            List<Address> addresses = new Geocoder(context, Locale.getDefault())
                .getFromLocation(location.getLatitude(), location.getLongitude(), 1);
            if (addresses != null && !addresses.isEmpty()) address = addresses.get(0);
        } catch (Exception ignored) {
        }
        String country = address != null && address.getCountryName() != null ? address.getCountryName() : "Taiwan";
        String cityLocal = "Kaohsiung";
        if (address != null) {
            if (address.getLocality() != null) cityLocal = address.getLocality();
            else if (address.getSubAdminArea() != null) cityLocal = address.getSubAdminArea();
            else if (address.getAdminArea() != null) cityLocal = address.getAdminArea();
        }
        return new CityInfo(cityLocal, EnglishCityNames.toEnglish(cityLocal), country, location.getLatitude(), location.getLongitude());
    }

    static WeatherInfo fetchWeather(Context context, double lat, double lon) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        String key = prefs.getString(AppConfig.KEY_OPENWEATHER, "");
        if (key == null || key.trim().isEmpty()) return new WeatherInfo("Cloudy", 27, 32);
        URL url = new URL("https://api.openweathermap.org/data/2.5/weather"
            + "?lat=" + lat + "&lon=" + lon + "&units=metric&appid=" + key.trim());
        JSONObject root = new JSONObject(Http.get(url, null));
        JSONObject main = root.getJSONObject("main");
        String weatherMain = root.getJSONArray("weather").getJSONObject(0).getString("main");
        return new WeatherInfo(
            WeatherMapper.normalize(weatherMain),
            (int) Math.round(main.getDouble("temp_min")),
            (int) Math.round(main.getDouble("temp_max"))
        );
    }
}

class WeatherScene {
    final String cityLocal;
    final String cityEnglish;
    final String country;
    final String date;
    final String time;
    final String weather;
    final int tempMin;
    final int tempMax;
    final String timePeriod;
    final List<String> landmarks;
    final String language;

    WeatherScene(String cityLocal, String cityEnglish, String country, String date, String time, String weather,
                 int tempMin, int tempMax, String timePeriod, List<String> landmarks, String language) {
        this.cityLocal = cityLocal;
        this.cityEnglish = cityEnglish;
        this.country = country;
        this.date = date;
        this.time = time;
        this.weather = weather;
        this.tempMin = tempMin;
        this.tempMax = tempMax;
        this.timePeriod = timePeriod;
        this.landmarks = landmarks;
        this.language = language;
    }
}

class CityInfo {
    final String cityLocal;
    final String cityEnglish;
    final String country;
    final double latitude;
    final double longitude;

    CityInfo(String cityLocal, String cityEnglish, String country, double latitude, double longitude) {
        this.cityLocal = cityLocal;
        this.cityEnglish = cityEnglish;
        this.country = country;
        this.latitude = latitude;
        this.longitude = longitude;
    }

    Location toLocation() {
        Location location = new Location(LocationManager.NETWORK_PROVIDER);
        location.setLatitude(latitude);
        location.setLongitude(longitude);
        location.setTime(System.currentTimeMillis());
        return location;
    }
}

class WeatherInfo {
    final String weather;
    final int tempMin;
    final int tempMax;

    WeatherInfo(String weather, int tempMin, int tempMax) {
        this.weather = weather;
        this.tempMin = tempMin;
        this.tempMax = tempMax;
    }
}

class WeatherTemplate {
    final String sky;
    final String effect;

    WeatherTemplate(String sky, String effect) {
        this.sky = sky;
        this.effect = effect;
    }
}

class SceneFactory {
    static WeatherScene create(CityInfo city, WeatherInfo weather) {
        LocalTime now = LocalTime.now();
        String english = city.cityEnglish == null || city.cityEnglish.trim().isEmpty() ? "Kaohsiung" : city.cityEnglish;
        return new WeatherScene(
            city.cityLocal,
            english,
            city.country,
            LocalDate.now().toString(),
            now.format(DateTimeFormatter.ofPattern("HH:mm")),
            weather.weather,
            weather.tempMin,
            weather.tempMax,
            Rules.getTimePeriod(now.getHour()),
            LandmarkDatabase.forCity(english),
            LanguageRules.forCountry(city.country)
        );
    }

    static WeatherScene createFallback() {
        LocalTime now = LocalTime.now();
        return new WeatherScene(
            "Kaohsiung",
            "Kaohsiung",
            "Taiwan",
            LocalDate.now().toString(),
            now.format(DateTimeFormatter.ofPattern("HH:mm")),
            "Cloudy",
            27,
            32,
            Rules.getTimePeriod(now.getHour()),
            LandmarkDatabase.forCity("Kaohsiung"),
            "Traditional Chinese"
        );
    }
}

class Rules {
    private static final Map<String, WeatherTemplate> WEATHER = new HashMap<>();
    private static final Map<String, String> TIME = new HashMap<>();

    static {
        WEATHER.put("Sunny", new WeatherTemplate("pastel blue sky", "crochet sun"));
        WEATHER.put("Cloudy", new WeatherTemplate("knitted clouds", "soft diffuse lighting"));
        WEATHER.put("Rainy", new WeatherTemplate("dark knitted sky", "crochet rain drops"));
        WEATHER.put("Snowy", new WeatherTemplate("white winter yarn landscape", "crochet snowflakes"));
        WEATHER.put("Foggy", new WeatherTemplate("felt fog", "soft dreamy atmosphere"));
        TIME.put("Morning", "soft sunrise");
        TIME.put("Afternoon", "bright warm daylight");
        TIME.put("Sunset", "orange pink sky");
        TIME.put("Evening", "warm street lights");
        TIME.put("Night", "deep blue knitted sky");
    }

    static String getTimePeriod(int hour) {
        if (hour >= 5 && hour <= 10) return "Morning";
        if (hour >= 11 && hour <= 16) return "Afternoon";
        if (hour >= 17 && hour <= 18) return "Sunset";
        if (hour >= 19 && hour <= 21) return "Evening";
        return "Night";
    }

    static WeatherTemplate weatherTemplate(String weather) {
        WeatherTemplate template = WEATHER.get(weather);
        return template != null ? template : WEATHER.get("Cloudy");
    }

    static String timeTemplate(String period) {
        String template = TIME.get(period);
        return template != null ? template : "warm street lights";
    }

    static String textColor(String weather, String period) {
        if ("Sunset".equals(period)) return "Deep Orange";
        if ("Night".equals(period)) return "Ivory White";
        if ("Cloudy".equals(weather)) return "Dark Gray";
        if ("Rainy".equals(weather)) return "Cream White";
        if ("Snowy".equals(weather)) return "Camel";
        if ("Sunny".equals(weather)) return "Dark Brown";
        return "Dark Gray";
    }
}

class WeatherMapper {
    static String normalize(String value) {
        if ("Clear".equals(value)) return "Sunny";
        if ("Clouds".equals(value)) return "Cloudy";
        if ("Rain".equals(value) || "Drizzle".equals(value) || "Thunderstorm".equals(value)) return "Rainy";
        if ("Snow".equals(value)) return "Snowy";
        if (Arrays.asList("Mist", "Fog", "Haze", "Smoke", "Dust", "Sand", "Ash", "Squall", "Tornado").contains(value)) return "Foggy";
        return value;
    }
}

class CityDatabase {
    private static final Map<String, CityInfo> DATA = new HashMap<>();

    static {
        DATA.put("taipei", new CityInfo("Taipei", "Taipei", "Taiwan", 25.0330, 121.5654));
        DATA.put("kaohsiung", new CityInfo("Kaohsiung", "Kaohsiung", "Taiwan", 22.6273, 120.3014));
        DATA.put("tokyo", new CityInfo("Tokyo", "Tokyo", "Japan", 35.6762, 139.6503));
        DATA.put("seoul", new CityInfo("Seoul", "Seoul", "South Korea", 37.5665, 126.9780));
        DATA.put("new york", new CityInfo("New York", "New York", "United States", 40.7128, -74.0060));
        DATA.put("paris", new CityInfo("Paris", "Paris", "France", 48.8566, 2.3522));
        DATA.put("berlin", new CityInfo("Berlin", "Berlin", "Germany", 52.5200, 13.4050));
    }

    static CityInfo forName(String raw) {
        String key = raw == null ? "" : raw.trim().toLowerCase(Locale.US);
        CityInfo city = DATA.get(key);
        if (city != null) return city;
        return new CityInfo(raw == null || raw.trim().isEmpty() ? "Kaohsiung" : raw.trim(),
            EnglishCityNames.toEnglish(raw == null ? "" : raw.trim()), "Taiwan", 22.6273, 120.3014);
    }
}

class LandmarkDatabase {
    private static final Map<String, List<String>> DATA = new HashMap<>();

    static {
        DATA.put("Taipei", Arrays.asList("Taipei 101", "Ximending", "Raohe Night Market"));
        DATA.put("Kaohsiung", Arrays.asList("85 Sky Tower", "Love River", "Pier-2 Art Center"));
        DATA.put("Tokyo", Arrays.asList("Tokyo Tower", "Shibuya Crossing", "Sensoji Temple"));
        DATA.put("Seoul", Arrays.asList("N Seoul Tower", "Gyeongbokgung", "Myeongdong"));
        DATA.put("New York", Arrays.asList("Empire State Building", "Times Square", "Brooklyn Bridge"));
        DATA.put("Paris", Arrays.asList("Eiffel Tower", "Louvre Museum", "Montmartre"));
        DATA.put("Berlin", Arrays.asList("Brandenburg Gate", "Berlin TV Tower", "Museum Island"));
    }

    static List<String> forCity(String cityEnglish) {
        List<String> landmarks = DATA.get(cityEnglish);
        return landmarks != null ? landmarks : Arrays.asList("central station", "old town market", "city park");
    }
}

class LanguageRules {
    private static final Map<String, String> DATA = new HashMap<>();

    static {
        DATA.put("Taiwan", "Traditional Chinese");
        DATA.put("China", "Simplified Chinese");
        DATA.put("Japan", "Japanese");
        DATA.put("South Korea", "Korean");
        DATA.put("Korea", "Korean");
        DATA.put("USA", "English");
        DATA.put("United States", "English");
        DATA.put("France", "French");
        DATA.put("Germany", "German");
    }

    static String forCountry(String country) {
        String language = DATA.get(country);
        return language != null ? language : "English";
    }
}

class EnglishCityNames {
    private static final Map<String, String> DATA = new HashMap<>();

    static {
        DATA.put("Taipei", "Taipei");
        DATA.put("Taipei City", "Taipei");
        DATA.put("Kaohsiung", "Kaohsiung");
        DATA.put("Kaohsiung City", "Kaohsiung");
        DATA.put("Tokyo", "Tokyo");
        DATA.put("Seoul", "Seoul");
        DATA.put("New York", "New York");
        DATA.put("Paris", "Paris");
        DATA.put("Berlin", "Berlin");
    }

    static String toEnglish(String cityLocal) {
        String mapped = DATA.get(cityLocal);
        if (mapped != null) return mapped;
        if (cityLocal == null || cityLocal.trim().isEmpty()) return "Kaohsiung";
        return cityLocal.replace(" City", "").trim();
    }
}

class PromptBuilder {
    static String build(WeatherScene scene) {
        WeatherTemplate weather = Rules.weatherTemplate(scene.weather);
        StringBuilder landmarks = new StringBuilder();
        for (int i = 0; i < scene.landmarks.size(); i++) {
            if (i > 0) landmarks.append(",\n");
            landmarks.append(scene.landmarks.get(i));
        }
        return "Create a premium Android wallpaper.\n\n"
            + "City:\n" + scene.cityEnglish + "\n\n"
            + "Date:\n" + scene.date + "\n\n"
            + "Temperature:\n" + scene.tempMin + "C~" + scene.tempMax + "C\n\n"
            + "Weather:\n" + scene.weather + "\n\n"
            + "Time:\n" + scene.timePeriod + "\n\n"
            + "Theme:\nMiniature Amigurumi crochet city.\n\n"
            + "Landmarks:\n" + landmarks + ".\n\n"
            + "All buildings, vehicles, people, shops, trees, and roads are handmade crochet toys.\n\n"
            + scene.language + " signs embroidered with yarn.\n\n"
            + weather.sky + ".\n\n"
            + weather.effect + ".\n\n"
            + Rules.timeTemplate(scene.timePeriod) + ".\n\n"
            + "Cute Amigurumi people walking and chatting.\n\n"
            + "Do not draw phone UI, clock, date, temperature text, status bar, widgets, app labels, or readable overlay text.\n\n"
            + "Leave the upper 25 percent visually clean so the Android lock screen can show its built-in clock and date.\n\n"
            + "Crochet " + scene.weather.toLowerCase(Locale.US) + " weather icon.\n\n"
            + "No text at top or bottom.\n\n"
            + "9:16 portrait wallpaper.";
    }
}

class ImageGenerator {
    static Bitmap generate(String apiKey, String model, String prompt) throws Exception {
        JSONObject body = new JSONObject()
            .put("model", model)
            .put("prompt", prompt)
            .put("size", "1024x1536")
            .put("n", 1);

        String json = Http.post(
            new URL("https://api.openai.com/v1/images/generations"),
            body.toString(),
            singletonHeader("Authorization", "Bearer " + apiKey)
        );
        JSONObject item = new JSONObject(json).getJSONArray("data").getJSONObject(0);
        String encoded = item.optString("b64_json");
        if (encoded != null && !encoded.isEmpty()) {
            byte[] bytes = Base64.decode(encoded, Base64.DEFAULT);
            return BitmapFactory.decodeStream(new ByteArrayInputStream(bytes));
        }
        String imageUrl = item.optString("url");
        if (imageUrl != null && !imageUrl.isEmpty()) {
            HttpURLConnection connection = (HttpURLConnection) new URL(imageUrl).openConnection();
            connection.setConnectTimeout(30000);
            connection.setReadTimeout(60000);
            return BitmapFactory.decodeStream(new BufferedInputStream(connection.getInputStream()));
        }
        return null;
    }

    private static Map<String, String> singletonHeader(String name, String value) {
        Map<String, String> headers = new HashMap<>();
        headers.put(name, value);
        return headers;
    }
}

class Http {
    static String get(URL url, Map<String, String> headers) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(20000);
        connection.setReadTimeout(30000);
        if (headers != null) for (Map.Entry<String, String> entry : headers.entrySet()) {
            connection.setRequestProperty(entry.getKey(), entry.getValue());
        }
        return read(connection);
    }

    static String post(URL url, String body, Map<String, String> headers) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(30000);
        connection.setReadTimeout(120000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json");
        for (Map.Entry<String, String> entry : headers.entrySet()) {
            connection.setRequestProperty(entry.getKey(), entry.getValue());
        }
        try (OutputStreamWriter writer = new OutputStreamWriter(connection.getOutputStream())) {
            writer.write(body);
        }
        return read(connection);
    }

    private static String read(HttpURLConnection connection) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(
            connection.getResponseCode() >= 200 && connection.getResponseCode() <= 299
                ? connection.getInputStream()
                : connection.getErrorStream()
        ));
        StringBuilder builder = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) builder.append(line);
        String body = builder.toString();
        if (connection.getResponseCode() < 200 || connection.getResponseCode() > 299) {
            throw new IllegalStateException("HTTP " + connection.getResponseCode() + ": " + body);
        }
        return body;
    }
}

class LocalWallpaperRenderer {
    static Bitmap render(WeatherScene scene) {
        int width = 1080;
        int height = 1920;
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        drawFrame(canvas, width, height, scene, 0);
        return bitmap;
    }

    static void drawFrame(Canvas canvas, int width, int height, WeatherScene scene, long frame) {
        drawBackground(canvas, width, height, scene);
        drawYarnSky(canvas, width, height, scene, frame);
        drawCity(canvas, width, height, scene, frame);
    }

    private static void drawBackground(Canvas canvas, int width, int height, WeatherScene scene) {
        int start;
        int end;
        switch (scene.timePeriod) {
            case "Morning":
                start = Color.rgb(255, 210, 155);
                end = Color.rgb(168, 217, 224);
                break;
            case "Afternoon":
                start = Color.rgb(145, 202, 224);
                end = Color.rgb(255, 230, 177);
                break;
            case "Sunset":
                start = Color.rgb(237, 126, 92);
                end = Color.rgb(255, 196, 150);
                break;
            case "Night":
                start = Color.rgb(27, 44, 78);
                end = Color.rgb(69, 84, 123);
                break;
            default:
                start = Color.rgb(97, 118, 150);
                end = Color.rgb(232, 175, 121);
        }
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setShader(new LinearGradient(0, 0, 0, height, start, end, Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, width, height, paint);
    }

    private static void drawYarnSky(Canvas canvas, int width, int height, WeatherScene scene, long frame) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setColor("Rainy".equals(scene.weather) ? Color.rgb(89, 92, 107) : Color.rgb(250, 247, 238));
        float yBase = height * 0.22f;
        float drift = (frame % 240) - 120;
        for (int i = 0; i < 6; i++) {
            float x = width * (0.10f + i * 0.16f) + drift * (i % 2 == 0 ? 0.35f : -0.25f);
            drawCrochetBlob(canvas, x, yBase + (i % 2) * 58f, 92f, paint);
        }
        if ("Sunny".equals(scene.weather)) {
            paint.setColor(Color.rgb(247, 189, 64));
            drawCrochetBlob(canvas, width * 0.82f, height * 0.18f, 100f + (frame % 30), paint);
        }
        if ("Rainy".equals(scene.weather)) {
            paint.setColor(Color.rgb(208, 225, 232));
            for (int i = 0; i < 34; i++) {
                float x = (i * 43 + frame * 5) % width;
                float y = height * 0.30f + ((i * 71 + frame * 13) % 760);
                canvas.drawOval(new RectF(x, y, x + 12f, y + 34f), paint);
            }
        }
    }

    private static void drawCity(Canvas canvas, int width, int height, WeatherScene scene, long frame) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        float ground = height * 0.72f;
        paint.setColor(Color.rgb(93, 116, 88));
        canvas.drawOval(new RectF(-80, ground, width + 80, height + 120), paint);

        int[] colors = {
            Color.rgb(234, 175, 108),
            Color.rgb(122, 166, 155),
            Color.rgb(214, 126, 104),
            Color.rgb(118, 93, 129)
        };
        for (int i = 0; i < Math.min(3, scene.landmarks.size()); i++) {
            paint.setColor(colors[i % colors.length]);
            float top = ground - 280f - i * 80f;
            float x = 110f + i * 240f;
            RectF rect = new RectF(x, top, x + 145f, ground + 40f);
            canvas.drawRoundRect(rect, 32f, 32f, paint);
            drawYarnLines(canvas, rect);
            if ("Evening".equals(scene.timePeriod) || "Night".equals(scene.timePeriod)) {
                drawWindows(canvas, rect, frame + i * 9);
            }
        }

        paint.setColor(Color.rgb(82, 67, 57));
        canvas.drawRoundRect(new RectF(width * 0.44f, ground - 520f, width * 0.56f, ground + 34f), 24f, 24f, paint);
        paint.setColor(Color.rgb(230, 215, 188));
        canvas.drawCircle(width * 0.50f, ground - 560f, 54f, paint);
        drawPeople(canvas, height, frame);
    }

    private static void drawYarnLines(Canvas canvas, RectF rect) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setColor(Color.argb(80, 255, 255, 255));
        paint.setStrokeWidth(5f);
        for (float y = rect.top + 28f; y < rect.bottom; y += 34f) {
            canvas.drawLine(rect.left + 18f, y, rect.right - 18f, y + 8f, paint);
        }
    }

    private static void drawWindows(Canvas canvas, RectF rect, long frame) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        for (int row = 0; row < 6; row++) {
            for (int col = 0; col < 3; col++) {
                int alpha = ((frame + row + col) % 24) < 12 ? 220 : 120;
                paint.setColor(Color.argb(alpha, 255, 221, 119));
                float x = rect.left + 25 + col * 36;
                float y = rect.top + 42 + row * 42;
                canvas.drawRoundRect(new RectF(x, y, x + 18, y + 18), 5, 5, paint);
            }
        }
    }

    private static void drawPeople(Canvas canvas, int height, long frame) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        for (int i = 0; i < 7; i++) {
            float walk = ((frame * 3 + i * 39) % 70) - 35;
            float x = 120f + i * 135f + walk;
            float y = height * 0.79f + (i % 2) * 42f;
            paint.setColor(Color.rgb(246, 202, 158));
            canvas.drawCircle(x, y, 24f, paint);
            paint.setColor(Color.rgb(115 + i * 14 % 90, 82 + i * 19 % 90, 88 + i * 11 % 80));
            canvas.drawRoundRect(new RectF(x - 26f, y + 24f, x + 26f, y + 92f), 18f, 18f, paint);
        }
    }

    private static void drawCrochetBlob(Canvas canvas, float centerX, float centerY, float radius, Paint paint) {
        int oldColor = paint.getColor();
        for (int i = 0; i < 9; i++) {
            double angle = Math.toRadians(i * 40d);
            float x = centerX + (float) Math.cos(angle) * radius * 0.5f;
            float y = centerY + (float) Math.sin(angle) * radius * 0.24f;
            canvas.drawCircle(x, y, radius * 0.36f, paint);
        }
        canvas.drawCircle(centerX, centerY, radius * 0.44f, paint);
        paint.setColor(Color.argb(80, 105, 86, 72));
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(5f);
        canvas.drawCircle(centerX, centerY, radius * 0.42f, paint);
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(oldColor);
    }

    static void drawWeatherOverlay(Canvas canvas, int width, int height, WeatherScene scene, long frame) {
        if ("Rainy".equals(scene.weather)) {
            Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
            paint.setColor(Color.argb(155, 220, 235, 242));
            for (int i = 0; i < 42; i++) {
                float x = (i * 61 + frame * 6) % width;
                float y = height * 0.20f + ((i * 89 + frame * 15) % (int) (height * 0.74f));
                canvas.drawOval(new RectF(x, y, x + 12f, y + 40f), paint);
            }
        }
        if ("Cloudy".equals(scene.weather) || "Foggy".equals(scene.weather)) {
            Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
            paint.setColor(Color.argb("Foggy".equals(scene.weather) ? 70 : 30, 245, 245, 235));
            float offset = (frame % 180) - 90;
            canvas.drawOval(new RectF(-120 + offset, height * 0.18f, width + 160 + offset, height * 0.48f), paint);
        }
    }
}
