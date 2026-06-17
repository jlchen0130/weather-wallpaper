package com.codex.amigurumiweather;

import android.Manifest;
import android.app.Activity;
import android.app.WallpaperManager;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.ContentResolver;
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
import android.graphics.Typeface;
import android.location.Address;
import android.location.Geocoder;
import android.location.Location;
import android.location.LocationManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.ArrayAdapter;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
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
    private static final int REQUEST_ADMIN_IMAGE = 2401;
    private SharedPreferences prefs;
    private TextView statusText;
    private ImageView preview;
    private EditText customCity;
    private CheckBox useCustomLocation;
    private CheckBox useCustomLanguage;
    private EditText customLanguage;
    private Spinner characterSpinner;
    private Spinner styleSpinner;
    private EditText adminToken;
    private EditText adminCity;
    private EditText adminCountry;
    private EditText adminTempMin;
    private EditText adminTempMax;
    private EditText adminLandmarks;
    private Spinner adminWeather;
    private Spinner adminPeriod;
    private Spinner adminCharacter;
    private Spinner adminStyle;
    private TextView adminPrompt;
    private TextView adminImageStatus;
    private Uri adminImageUri;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        if (isAdminApp()) {
            setContentView(buildAdminUi());
        } else {
            setContentView(buildUi());
            requestLocationPermissionIfNeeded();
        }
    }

    private boolean isAdminApp() {
        return getPackageName().endsWith(".admin");
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
        subtitle.setText("\u81ea\u52d5\u4f9d\u5730\u9ede\u3001\u5929\u6c23\u8207\u5929\u8272\u66f4\u65b0\u52d5\u614b\u684c\u5e03\u3002API \u8207\u4f3a\u670d\u5668\u8a2d\u5b9a\u5df2\u96b1\u85cf\u3002");
        subtitle.setTextSize(14f);
        subtitle.setTextColor(Color.rgb(92, 74, 62));
        subtitle.setPadding(0, dp(6), 0, dp(14));
        root.addView(subtitle);

        useCustomLocation = new CheckBox(this);
        useCustomLocation.setText("\u5730\u9ede\uff1a\u4f7f\u7528\u81ea\u8a02\u5730\u9ede\uff0c\u4e0d\u4f7f\u7528 GPS \u5b9a\u4f4d");
        useCustomLocation.setChecked(prefs.getBoolean(AppConfig.KEY_USE_CUSTOM, false));
        root.addView(useCustomLocation);

        customCity = input("\u81ea\u8a02\u5730\u9ede\uff1aKaohsiung / Taipei / Tokyo", AppConfig.KEY_CUSTOM_CITY, false);
        if (customCity.getText().toString().trim().isEmpty()) {
            customCity.setText("Kaohsiung");
        }
        root.addView(customCity);

        useCustomLanguage = new CheckBox(this);
        useCustomLanguage.setText("\u8a9e\u8a00\u8a2d\u5b9a\uff1a\u4f7f\u7528\u81ea\u5b9a\u7fa9\u8a9e\u7a2e\uff0c\u4e0d\u81ea\u52d5\u5075\u6e2c\u7cfb\u7d71\u9810\u8a2d");
        useCustomLanguage.setChecked(prefs.getBoolean(AppConfig.KEY_USE_CUSTOM_LANGUAGE, false));
        root.addView(useCustomLanguage);

        customLanguage = input("\u81ea\u5b9a\u7fa9\u8a9e\u7a2e\uff1aTraditional Chinese / English / Japanese", AppConfig.KEY_CUSTOM_LANGUAGE, false);
        if (customLanguage.getText().toString().trim().isEmpty()) {
            customLanguage.setText("Traditional Chinese");
        }
        root.addView(customLanguage);

        TextView characterLabel = new TextView(this);
        characterLabel.setText("\u684c\u5e03\u4e3b\u89d2");
        characterLabel.setTextSize(14f);
        characterLabel.setTextColor(Color.rgb(65, 45, 34));
        characterLabel.setPadding(0, dp(8), 0, 0);
        root.addView(characterLabel);

        characterSpinner = new Spinner(this);
        ArrayAdapter<String> characterAdapter = new ArrayAdapter<>(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            CharacterOptions.LABELS
        );
        characterAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        characterSpinner.setAdapter(characterAdapter);
        characterSpinner.setSelection(CharacterOptions.indexOf(prefs.getString(AppConfig.KEY_CHARACTER, "person")));
        root.addView(characterSpinner);

        TextView styleLabel = new TextView(this);
        styleLabel.setText("\u756b\u98a8");
        styleLabel.setTextSize(14f);
        styleLabel.setTextColor(Color.rgb(65, 45, 34));
        styleLabel.setPadding(0, dp(8), 0, 0);
        root.addView(styleLabel);

        styleSpinner = new Spinner(this);
        ArrayAdapter<String> styleAdapter = new ArrayAdapter<>(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            StyleOptions.LABELS
        );
        styleAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        styleSpinner.setAdapter(styleAdapter);
        styleSpinner.setSelection(StyleOptions.indexOf(prefs.getString(AppConfig.KEY_STYLE, "knitted")));
        root.addView(styleSpinner);

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER);
        row.setPadding(0, dp(10), 0, dp(10));

        Button save = new Button(this);
        save.setText("\u5132\u5b58");
        save.setOnClickListener(v -> saveSettings());
        LinearLayout.LayoutParams saveParams = new LinearLayout.LayoutParams(0, dp(48), 1f);
        saveParams.setMarginEnd(dp(8));
        row.addView(save, saveParams);

        Button generate = new Button(this);
        generate.setText("\u8a2d\u5b9a\u975c\u614b\u684c\u5e03");
        generate.setOnClickListener(v -> {
            saveSettings();
            generateAndApplyWallpaper();
        });
        row.addView(generate, new LinearLayout.LayoutParams(0, dp(48), 1.4f));
        root.addView(row);

        Button live = new Button(this);
        live.setText("\u958b\u555f\u52d5\u614b\u684c\u5e03");
        live.setOnClickListener(v -> {
            saveSettings();
            openLiveWallpaperPicker();
        });
        root.addView(live, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(48)));

        Button update = new Button(this);
        update.setText("\u66f4\u65b0 App");
        update.setOnClickListener(v -> {
            saveSettings();
            checkAndDownloadUpdate();
        });
        root.addView(update, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(48)));

        TextView version = new TextView(this);
        version.setText("App \u7248\u672c\uff1a" + AppUpdater.currentVersionName(this));
        version.setTextSize(13f);
        version.setTextColor(Color.rgb(92, 74, 62));
        version.setGravity(Gravity.CENTER);
        version.setPadding(0, dp(6), 0, dp(8));
        root.addView(version);

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

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        return scroll;
    }

    private View buildAdminUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(28));
        root.setBackgroundColor(Color.rgb(255, 248, 239));

        TextView title = new TextView(this);
        title.setText("Weather Wallpaper Admin");
        title.setTextSize(24f);
        title.setTextColor(Color.rgb(65, 45, 34));
        title.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("\u7528\u65bc API \u984d\u5ea6\u4e0d\u8db3\u6642\uff1a\u7522\u751f\u63d0\u793a\u8a5e\u3001\u8907\u88fd\u5230 ChatGPT\u3001\u9078\u53d6\u5716\u7247\u4e26\u4e0a\u50b3 R2\u3002");
        subtitle.setTextSize(14f);
        subtitle.setTextColor(Color.rgb(92, 74, 62));
        subtitle.setPadding(0, dp(6), 0, dp(12));
        root.addView(subtitle);

        adminToken = input("\u4e0a\u50b3 token", "admin_upload_token", true);
        root.addView(adminToken);

        adminCity = input("\u57ce\u5e02\uff1aKaohsiung", "admin_city", false);
        if (adminCity.getText().toString().trim().isEmpty()) adminCity.setText("Kaohsiung");
        root.addView(adminCity);

        adminCountry = input("\u570b\u5bb6\uff1aTaiwan", "admin_country", false);
        if (adminCountry.getText().toString().trim().isEmpty()) adminCountry.setText("Taiwan");
        root.addView(adminCountry);

        adminWeather = spinner(new String[] {"晴", "多云", "阴", "阵雨", "雷阵雨", "雷阵雨伴有冰雹", "雨夹雪", "小雨", "中雨", "大雨", "暴雨", "大暴雨", "特大暴雨", "阵雪", "小雪", "中雪", "大雪", "暴雪", "雾", "冻雨", "沙尘暴", "小雨-中雨", "中雨-大雨", "大雨-暴雨", "暴雨-大暴雨", "大暴雨-特大暴雨", "小雪-中雪", "中雪-大雪", "大雪-暴雪", "浮尘", "扬沙", "强沙尘暴", "霾"}, prefs.getString("admin_weather", "晴"));
        root.addView(label("\u5929\u6c23"));
        root.addView(adminWeather);

        adminPeriod = spinner(new String[] {"sunraise", "Morning", "Afternoon", "Sunset", "Night", "Midnight"}, prefs.getString("admin_period", "Afternoon"));
        root.addView(label("\u6642\u6bb5"));
        root.addView(adminPeriod);

        adminCharacter = spinner(CharacterOptions.LABELS, CharacterOptions.LABELS[CharacterOptions.indexOf(prefs.getString("admin_character", "person"))]);
        root.addView(label("\u4e3b\u89d2"));
        root.addView(adminCharacter);

        adminStyle = spinner(StyleOptions.LABELS, StyleOptions.LABELS[StyleOptions.indexOf(prefs.getString("admin_style", "knitted"))]);
        root.addView(label("\u756b\u98a8"));
        root.addView(adminStyle);

        adminTempMin = input("\u6700\u4f4e\u6eab", "admin_temp_min", false);
        if (adminTempMin.getText().toString().trim().isEmpty()) adminTempMin.setText("27");
        root.addView(adminTempMin);

        adminTempMax = input("\u6700\u9ad8\u6eab", "admin_temp_max", false);
        if (adminTempMax.getText().toString().trim().isEmpty()) adminTempMax.setText("32");
        root.addView(adminTempMax);

        adminLandmarks = input("\u666f\u9ede\uff0c\u7528 | \u5206\u9694", "admin_landmarks", false);
        if (adminLandmarks.getText().toString().trim().isEmpty()) {
            adminLandmarks.setText("85 Sky Tower|Love River|Pier-2 Art Center");
        }
        root.addView(adminLandmarks);

        Button promptButton = new Button(this);
        promptButton.setText("\u7522\u751f\u4e26\u8907\u88fd\u63d0\u793a\u8a5e");
        promptButton.setOnClickListener(v -> {
            saveAdminSettings();
            copyAdminPrompt();
        });
        root.addView(promptButton, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(48)));

        Button shareButton = new Button(this);
        shareButton.setText("\u5206\u4eab\u63d0\u793a\u8a5e\u5230 GPT App");
        shareButton.setOnClickListener(v -> shareAdminPrompt());
        root.addView(shareButton, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(48)));

        adminPrompt = new TextView(this);
        adminPrompt.setText(buildAdminPrompt());
        adminPrompt.setTextSize(12f);
        adminPrompt.setTextColor(Color.rgb(65, 45, 34));
        adminPrompt.setPadding(dp(10), dp(10), dp(10), dp(10));
        adminPrompt.setBackgroundColor(Color.rgb(241, 224, 204));
        root.addView(adminPrompt);

        Button choose = new Button(this);
        choose.setText("\u9078\u53d6 GPT \u7522\u51fa\u5716\u7247");
        choose.setOnClickListener(v -> pickAdminImage());
        root.addView(choose, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(48)));

        Button upload = new Button(this);
        upload.setText("\u4e0a\u50b3\u5230 R2 \u4e26\u63a8\u9001\u7d66\u624b\u6a5f App");
        upload.setOnClickListener(v -> {
            saveAdminSettings();
            uploadAdminImage();
        });
        root.addView(upload, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(48)));

        adminImageStatus = new TextView(this);
        adminImageStatus.setText("Status: ready");
        adminImageStatus.setTextSize(14f);
        adminImageStatus.setTextColor(Color.rgb(65, 45, 34));
        adminImageStatus.setPadding(0, dp(10), 0, 0);
        root.addView(adminImageStatus);

        TextView version = new TextView(this);
        version.setText("Admin APK \u7248\u672c\uff1a" + AppUpdater.currentVersionName(this));
        version.setGravity(Gravity.CENTER);
        version.setPadding(0, dp(8), 0, 0);
        root.addView(version);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        return scroll;
    }

    private TextView label(String value) {
        TextView text = new TextView(this);
        text.setText(value);
        text.setTextSize(13f);
        text.setTextColor(Color.rgb(65, 45, 34));
        text.setPadding(0, dp(8), 0, 0);
        return text;
    }

    private Spinner spinner(String[] values, String selected) {
        Spinner spinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, values);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(adapter);
        for (int i = 0; i < values.length; i++) {
            if (values[i].equals(selected)) {
                spinner.setSelection(i);
                break;
            }
        }
        return spinner;
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
        prefs.edit()
            .putBoolean(AppConfig.KEY_USE_CUSTOM, useCustomLocation.isChecked())
            .putString(AppConfig.KEY_CUSTOM_CITY, customCity.getText().toString().trim())
            .putBoolean(AppConfig.KEY_USE_CUSTOM_LANGUAGE, useCustomLanguage.isChecked())
            .putString(AppConfig.KEY_CUSTOM_LANGUAGE, customLanguage.getText().toString().trim())
            .putString(AppConfig.KEY_CHARACTER, CharacterOptions.valueAt(characterSpinner.getSelectedItemPosition()))
            .putString(AppConfig.KEY_STYLE, StyleOptions.valueAt(styleSpinner.getSelectedItemPosition()))
            .putString(AppConfig.KEY_UPDATE_MINUTES, Integer.toString(AppConfig.DEFAULT_UPDATE_MINUTES))
            .putString(AppConfig.KEY_WEATHER_BACKEND_URL, "")
            .putString(AppConfig.KEY_THEME_SERVER_URL, AppConfig.DEFAULT_THEME_SERVER_URL)
            .apply();
        Toast.makeText(this, "\u5df2\u5132\u5b58", Toast.LENGTH_SHORT).show();
    }

    private void saveAdminSettings() {
        prefs.edit()
            .putString("admin_upload_token", adminToken.getText().toString().trim())
            .putString("admin_city", adminCity.getText().toString().trim())
            .putString("admin_country", adminCountry.getText().toString().trim())
            .putString("admin_weather", adminWeather.getSelectedItem().toString())
            .putString("admin_period", adminPeriod.getSelectedItem().toString())
            .putString("admin_character", CharacterOptions.valueAt(adminCharacter.getSelectedItemPosition()))
            .putString("admin_style", StyleOptions.valueAt(adminStyle.getSelectedItemPosition()))
            .putString("admin_temp_min", adminTempMin.getText().toString().trim())
            .putString("admin_temp_max", adminTempMax.getText().toString().trim())
            .putString("admin_landmarks", adminLandmarks.getText().toString().trim())
            .apply();
    }

    private String buildAdminPrompt() {
        String city = adminCity == null ? prefs.getString("admin_city", "Kaohsiung") : adminCity.getText().toString().trim();
        String country = adminCountry == null ? prefs.getString("admin_country", "Taiwan") : adminCountry.getText().toString().trim();
        String weather = adminWeather == null ? prefs.getString("admin_weather", "Cloudy") : adminWeather.getSelectedItem().toString();
        String period = adminPeriod == null ? prefs.getString("admin_period", "Afternoon") : adminPeriod.getSelectedItem().toString();
        String character = adminCharacter == null ? prefs.getString("admin_character", "person") : CharacterOptions.valueAt(adminCharacter.getSelectedItemPosition());
        String style = adminStyle == null ? prefs.getString("admin_style", "knitted") : StyleOptions.valueAt(adminStyle.getSelectedItemPosition());
        String min = adminTempMin == null ? prefs.getString("admin_temp_min", "27") : adminTempMin.getText().toString().trim();
        String max = adminTempMax == null ? prefs.getString("admin_temp_max", "32") : adminTempMax.getText().toString().trim();
        String landmarks = adminLandmarks == null ? prefs.getString("admin_landmarks", "85 Sky Tower|Love River|Pier-2 Art Center") : adminLandmarks.getText().toString().trim();
        String characterText = CharacterOptions.promptText(character);
        String styleText = StyleOptions.promptText(style);
        return "手機動態桌布插畫，直式 9:16，高解析度，溫暖可愛的童話氛圍。\n"
            + styleText + "\n"
            + "City: " + cleanOr(city, "Kaohsiung") + ". Country: " + cleanOr(country, "Taiwan") + ".\n"
            + "Weather: " + weather + ". Time period: " + period + ". Temperature: " + cleanOr(min, "27") + "C~" + cleanOr(max, "32") + "C.\n"
            + "Landmarks: " + cleanOr(landmarks, "85 Sky Tower|Love River|Pier-2 Art Center").replace("|", ", ") + ".\n"
            + "Background融合 8 個當地知名景點，以微縮地景與童話城市的方式自然分布，不要像拼貼。\n"
            + "Use a distant wide-angle establishing view from a slightly elevated viewpoint, so landmarks are distributed naturally across the city scene with open sky and readable depth.\n"
            + "If the weather is sunny and hot, show soft golden sunlight, pale blue sky, fluffy white clouds, slight heat shimmer, tree shadows, and clear highlights.\n"
            + characterText + "\n"
            + "Characters should look active and varied, with poses that imply motion and daily life instead of standing still.\n"
            + "Add subtle visual motion cues suitable for a live wallpaper background: drifting clouds, tiny boats on water, walking poses, fluttering awnings, falling rain or snow when weather requires it, wind lines, sparkling highlights, and lively daily movement.\n"
            + "Keep the upper sky area light, calm, open, and visually clean for phone time/date widgets.\n"
            + "Avoid text, logo, watermark, phone UI, clock, date, battery, signal icons, app labels, temperature widgets, large labels, and poster-like typography.";
    }

    private void copyAdminPrompt() {
        String prompt = buildAdminPrompt();
        adminPrompt.setText(prompt);
        ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        clipboard.setPrimaryClip(ClipData.newPlainText("wallpaper prompt", prompt));
        adminImageStatus.setText("Status: prompt copied. Paste it into ChatGPT.");
    }

    private void shareAdminPrompt() {
        String prompt = buildAdminPrompt();
        adminPrompt.setText(prompt);
        ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        clipboard.setPrimaryClip(ClipData.newPlainText("wallpaper prompt", prompt));
        Intent send = new Intent(Intent.ACTION_SEND);
        send.setType("text/plain");
        send.putExtra(Intent.EXTRA_TEXT, prompt);
        startActivity(Intent.createChooser(send, "Share prompt"));
    }

    private void pickAdminImage() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("image/*");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        startActivityForResult(intent, REQUEST_ADMIN_IMAGE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_ADMIN_IMAGE && resultCode == RESULT_OK && data != null && data.getData() != null) {
            adminImageUri = data.getData();
            try {
                getContentResolver().takePersistableUriPermission(adminImageUri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
            } catch (Exception ignored) {
                // Some gallery providers return a readable URI without persistable permissions.
            }
            if (adminImageStatus != null) adminImageStatus.setText("Status: image selected.");
        }
    }

    private void uploadAdminImage() {
        if (adminImageUri == null) {
            adminImageStatus.setText("Status: select an image first.");
            return;
        }
        adminImageStatus.setText("Status: uploading to R2...");
        executor.execute(() -> {
            try {
                String result = uploadManualWallpaper();
                runOnUiThread(() -> adminImageStatus.setText("Status: uploaded. Phone apps will sync latest wallpaper.\n" + result));
            } catch (Exception error) {
                runOnUiThread(() -> adminImageStatus.setText("Status: upload failed. " + error.getMessage()));
            }
        });
    }

    private String uploadManualWallpaper() throws Exception {
        String boundary = "----amigurumi" + System.currentTimeMillis();
        URL url = new URL(AppConfig.DEFAULT_THEME_SERVER_URL + "/admin/upload");
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(30000);
        connection.setReadTimeout(120000);
        connection.setDoOutput(true);
        connection.setRequestMethod("POST");
        connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        try (DataOutputStream out = new DataOutputStream(connection.getOutputStream())) {
            writeField(out, boundary, "token", adminToken.getText().toString().trim());
            writeField(out, boundary, "city", cleanOr(adminCity.getText().toString(), "Kaohsiung"));
            writeField(out, boundary, "cityLocal", cleanOr(adminCity.getText().toString(), "Kaohsiung"));
            writeField(out, boundary, "country", cleanOr(adminCountry.getText().toString(), "Taiwan"));
            writeField(out, boundary, "date", LocalDate.now().format(DateTimeFormatter.ISO_DATE));
            writeField(out, boundary, "weather", adminWeather.getSelectedItem().toString());
            writeField(out, boundary, "period", adminPeriod.getSelectedItem().toString());
            writeField(out, boundary, "character", CharacterOptions.valueAt(adminCharacter.getSelectedItemPosition()));
            writeField(out, boundary, "style", StyleOptions.valueAt(adminStyle.getSelectedItemPosition()));
            writeField(out, boundary, "tempMin", cleanOr(adminTempMin.getText().toString(), "27"));
            writeField(out, boundary, "tempMax", cleanOr(adminTempMax.getText().toString(), "32"));
            writeField(out, boundary, "landmarks", cleanOr(adminLandmarks.getText().toString(), "85 Sky Tower|Love River|Pier-2 Art Center"));
            writeFile(out, boundary, adminImageUri);
            out.writeBytes("--" + boundary + "--\r\n");
        }
        String body = Http.read(connection);
        if (connection.getResponseCode() < 200 || connection.getResponseCode() > 299) {
            throw new IllegalStateException("HTTP " + connection.getResponseCode() + " " + body);
        }
        return body;
    }

    private void writeField(DataOutputStream out, String boundary, String name, String value) throws Exception {
        out.writeBytes("--" + boundary + "\r\n");
        out.writeBytes("Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n");
        out.write(value.getBytes("UTF-8"));
        out.writeBytes("\r\n");
    }

    private void writeFile(DataOutputStream out, String boundary, Uri uri) throws Exception {
        ContentResolver resolver = getContentResolver();
        String type = resolver.getType(uri);
        if (type == null || type.trim().isEmpty()) type = "image/png";
        out.writeBytes("--" + boundary + "\r\n");
        out.writeBytes("Content-Disposition: form-data; name=\"image\"; filename=\"wallpaper." + extensionFor(type) + "\"\r\n");
        out.writeBytes("Content-Type: " + type + "\r\n\r\n");
        try (InputStream input = resolver.openInputStream(uri)) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) out.write(buffer, 0, read);
        }
        out.writeBytes("\r\n");
    }

    private String cleanOr(String value, String fallback) {
        if (value == null || value.trim().isEmpty()) return fallback;
        return value.trim();
    }

    private String extensionFor(String type) {
        if ("image/jpeg".equals(type)) return "jpg";
        if ("image/webp".equals(type)) return "webp";
        return "png";
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
        prefs.edit().putString(AppConfig.KEY_WALLPAPER_MODE, AppConfig.WALLPAPER_MODE_STATIC).apply();
        executor.execute(() -> {
            try {
                WeatherScene scene = SceneResolver.resolve(this);
                Bitmap bitmap = ServerWallpaperClient.fetchOrCreate(this, scene);
                boolean usedFallback = false;
                if (bitmap == null && ServerWallpaperClient.isConfigured(this)) {
                    Bitmap cached = WallpaperStore.load(this);
                    if (cached != null) {
                        bitmap = cached;
                        usedFallback = true;
                        status("Status: server image not available. Applying cached wallpaper. " + ServerWallpaperClient.lastError());
                    } else {
                        bitmap = LocalWallpaperRenderer.render(scene);
                        usedFallback = true;
                        status("Status: server image not available. Applying local fallback wallpaper. " + ServerWallpaperClient.lastError());
                    }
                }
                if (bitmap == null) {
                    bitmap = LocalWallpaperRenderer.render(scene);
                    usedFallback = true;
                }
                WallpaperStore.save(this, bitmap);
                Bitmap previewBitmap = bitmap;
                runOnUiThread(() -> {
                    preview.setImageBitmap(Bitmap.createScaledBitmap(previewBitmap, 360, 640, true));
                    statusText.setText("Status: server wallpaper ready. Applying to phone...");
                });

                WallpaperManager.getInstance(this).setBitmap(bitmap);
                prefs.edit().putString(AppConfig.KEY_LAST_SCENE_KEY, SceneKeys.forContext(this, scene)).apply();
                Bitmap finalBitmap = bitmap;
                String source = usedFallback ? "fallback" : "server";
                runOnUiThread(() -> {
                    preview.setImageBitmap(Bitmap.createScaledBitmap(finalBitmap, 360, 640, true));
                    statusText.setText("Status: " + source + " wallpaper set for " + scene.cityEnglish + ", " + scene.weather + ", " + scene.tempMin + "C~" + scene.tempMax + "C.");
                });
            } catch (Exception error) {
                if (ServerWallpaperClient.isConfigured(this)) {
                    applyCachedWallpaper("Status: connection error. Keeping the last static wallpaper. " + error.getMessage(), true);
                } else {
                    WeatherScene scene = SceneFactory.createFallback();
                    Bitmap bitmap = LocalWallpaperRenderer.render(scene);
                    try {
                        WallpaperStore.save(this, bitmap);
                        WallpaperManager.getInstance(this).setBitmap(bitmap);
                    } catch (Exception ignored) {
                    }
                    runOnUiThread(() -> {
                        preview.setImageBitmap(Bitmap.createScaledBitmap(bitmap, 360, 640, true));
                        statusText.setText("Status: fallback wallpaper. " + error.getMessage());
                    });
                }
            }
        });
    }

    private void applyCachedWallpaper(String message) {
        applyCachedWallpaper(message, AppConfig.WALLPAPER_MODE_STATIC.equals(
            prefs.getString(AppConfig.KEY_WALLPAPER_MODE, AppConfig.WALLPAPER_MODE_STATIC)));
    }

    private void applyCachedWallpaper(String message, boolean applyStaticWallpaper) {
        Bitmap cached = WallpaperStore.load(this);
        if (cached == null) {
            runOnUiThread(() -> statusText.setText(message + " No cached wallpaper found yet."));
            return;
        }
        if (applyStaticWallpaper) {
            try {
                WallpaperManager.getInstance(this).setBitmap(cached);
            } catch (Exception ignored) {
            }
        }
        runOnUiThread(() -> {
            preview.setImageBitmap(Bitmap.createScaledBitmap(cached, 360, 640, true));
            statusText.setText(message);
        });
    }

    private void openLiveWallpaperPicker() {
        prefs.edit().putString(AppConfig.KEY_WALLPAPER_MODE, AppConfig.WALLPAPER_MODE_DYNAMIC).apply();
        try {
            Intent intent = new Intent(WallpaperManager.ACTION_CHANGE_LIVE_WALLPAPER);
            intent.putExtra(WallpaperManager.EXTRA_LIVE_WALLPAPER_COMPONENT,
                new ComponentName(this, DynamicWallpaperService.class));
            startActivity(intent);
        } catch (Exception error) {
            startActivity(new Intent(WallpaperManager.ACTION_LIVE_WALLPAPER_CHOOSER));
        }
    }

    private void checkAndDownloadUpdate() {
        status("Status: checking GitHub release for this device...");
        executor.execute(() -> {
            try {
                UpdateAsset asset = AppUpdater.findBestAsset();
                if (asset == null) {
                    status("Status: no APK asset found in latest GitHub release.");
                    return;
                }
                int currentVersion = AppUpdater.currentVersionCode(this);
                if (asset.versionCode <= currentVersion) {
                    status("Status: already on the latest version (" + AppUpdater.currentVersionName(this) + ").");
                    return;
                }
                status("Status: downloading " + asset.name + "...");
                File apk = AppUpdater.download(this, asset);
                Uri uri = Uri.parse("content://" + getPackageName() + ".apkprovider/" + apk.getName());
                Intent intent = new Intent(Intent.ACTION_VIEW);
                intent.setDataAndType(uri, "application/vnd.android.package-archive");
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
                status("Status: installer opened for " + asset.name + ".");
            } catch (Exception error) {
                status("Status: update failed. " + error.getMessage());
            }
        });
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
    static final String DEFAULT_THEME_SERVER_URL = "https://amigurumi-weather-theme-server.wemmei0130.workers.dev";
    static final int DEFAULT_UPDATE_MINUTES = 30;
    static final String KEY_WEATHER_BACKEND_URL = "weather_backend_url";
    static final String KEY_THEME_SERVER_URL = "theme_server_url";
    static final String KEY_USE_CUSTOM = "use_custom_location";
    static final String KEY_CUSTOM_CITY = "custom_city";
    static final String KEY_USE_CUSTOM_LANGUAGE = "use_custom_language";
    static final String KEY_CUSTOM_LANGUAGE = "custom_language";
    static final String KEY_CHARACTER = "character";
    static final String KEY_STYLE = "style";
    static final String KEY_UPDATE_MINUTES = "update_minutes";
    static final String KEY_LAST_SCENE_KEY = "last_scene_key";
    static final String KEY_LAST_SERVER_FILE = "last_server_file";
    static final String KEY_WALLPAPER_MODE = "wallpaper_mode";
    static final String WALLPAPER_MODE_STATIC = "static";
    static final String WALLPAPER_MODE_DYNAMIC = "dynamic";
    static final String LAST_WALLPAPER_FILE = "last_wallpaper.png";
    static final String TEMP_WALLPAPER_FILE = "last_wallpaper.tmp";

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

class CharacterOptions {
    static final String[] LABELS = {
        "\u4eba",
        "\u8c93",
        "\u72d7",
        "\u5009\u9f20/\u9f8d\u8c93"
    };
    private static final String[] VALUES = {
        "person",
        "cat",
        "dog",
        "hamster_chinchilla"
    };

    static int indexOf(String value) {
        for (int i = 0; i < VALUES.length; i++) {
            if (VALUES[i].equals(value)) return i;
        }
        return 0;
    }

    static String valueAt(int index) {
        if (index < 0 || index >= VALUES.length) return VALUES[0];
        return VALUES[index];
    }

    static String promptText(String value) {
        if ("cat".equals(value)) {
            return "Main characters are varied cute Q-version cats: tabby cats, calico cats, black cats, white cats, orange cats, and fluffy round cats doing daily life actions.";
        }
        if ("hamster_chinchilla".equals(value) || "hamster".equals(value)) {
            return "Main characters are cute Q-version hamsters and chinchillas with round bodies, soft ears, tiny bags, and everyday city-life actions.";
        }
        if ("dog".equals(value)) {
            return "Main characters are cute Q-version dogs of varied small breeds doing daily life actions, with friendly expressions and playful movement.";
        }
        return "Main character is a cute Q-version girl with a round face and big eyes, wearing fresh summer clothes, smiling in the foreground, holding a small fan and an iced drink, joined by a few friendly city residents in daily-life actions.";
    }
}

class StyleOptions {
    static final String[] LABELS = {
        "\u91dd\u7e54",
        "\u8272\u925b\u7b46"
    };
    private static final String[] VALUES = {
        "knitted",
        "colored_pencil"
    };

    static int indexOf(String value) {
        for (int i = 0; i < VALUES.length; i++) {
            if (VALUES[i].equals(value)) return i;
        }
        return 0;
    }

    static String valueAt(int index) {
        if (index < 0 || index >= VALUES.length) return VALUES[0];
        return VALUES[index];
    }

    static String promptText(String value) {
        if ("colored_pencil".equals(value)) {
            return "Use a refined colored pencil illustration style, soft paper grain, warm fairy-tale mood, clean depth, delicate hand-drawn strokes, gentle shading, and rich but soft color suitable for a phone live wallpaper.";
        }
        return "Use a premium handmade knitted and crochet amigurumi style: yarn texture, soft fiber depth, plush miniature buildings, crochet clouds, stitched details, and cozy handcrafted lighting suitable for a phone live wallpaper.";
    }
}

class UpdateAsset {
    final String name;
    final String url;
    final int versionCode;
    final String versionName;

    UpdateAsset(String name, String url, int versionCode, String versionName) {
        this.name = name;
        this.url = url;
        this.versionCode = versionCode;
        this.versionName = versionName;
    }
}

class AppUpdater {
    static UpdateAsset findBestAsset() throws Exception {
        JSONObject release = new JSONObject(Http.get(
            new URL("https://api.github.com/repos/jlchen0130/weather-wallpaper/releases/latest"), null));
        String versionName = release.optString("tag_name", release.optString("name", ""));
        int versionCode = versionCodeFromName(versionName);
        org.json.JSONArray assets = release.getJSONArray("assets");
        String model = (Build.MANUFACTURER + " " + Build.MODEL + " " + Build.DEVICE).toLowerCase(Locale.US);
        boolean samsungU23 = model.contains("samsung") && (model.contains("u23") || model.contains("s23"));
        boolean galaxyZFold5 = model.contains("samsung")
            && (model.contains("fold5") || model.contains("fold 5") || model.contains("f946"));
        UpdateAsset fallback = null;
        for (int i = 0; i < assets.length(); i++) {
            JSONObject item = assets.getJSONObject(i);
            String name = item.getString("name");
            if (!name.toLowerCase(Locale.US).endsWith(".apk")) continue;
            String url = item.getString("browser_download_url");
            String lower = name.toLowerCase(Locale.US);
            if (galaxyZFold5 && (lower.contains("zfold5") || lower.contains("z-fold-5") || lower.contains("fold5"))) {
                return new UpdateAsset(name, url, versionCode, versionName);
            }
            if (samsungU23 && lower.contains("samsung") && (lower.contains("u23") || lower.contains("s23"))) {
                return new UpdateAsset(name, url, versionCode, versionName);
            }
            if (fallback == null && (lower.contains("universal") || lower.contains("debug") || lower.contains("theme"))) {
                fallback = new UpdateAsset(name, url, versionCode, versionName);
            }
        }
        return fallback;
    }

    static int currentVersionCode(Context context) {
        try {
            if (Build.VERSION.SDK_INT >= 28) {
                return (int) context.getPackageManager()
                    .getPackageInfo(context.getPackageName(), 0)
                    .getLongVersionCode();
            }
            return context.getPackageManager().getPackageInfo(context.getPackageName(), 0).versionCode;
        } catch (Exception ignored) {
            return 0;
        }
    }

    static String currentVersionName(Context context) {
        try {
            return context.getPackageManager().getPackageInfo(context.getPackageName(), 0).versionName;
        } catch (Exception ignored) {
            return "current";
        }
    }

    private static int versionCodeFromName(String raw) {
        if (raw == null) return 0;
        String clean = raw.trim().toLowerCase(Locale.US);
        if (clean.startsWith("v")) clean = clean.substring(1);
        String[] parts = clean.split("\\.");
        try {
            if (parts.length >= 2) {
                int major = Integer.parseInt(parts[0].replaceAll("[^0-9]", ""));
                int minor = Integer.parseInt(parts[1].replaceAll("[^0-9]", ""));
                int patch = 0;
                if (parts.length >= 3) {
                    patch = Integer.parseInt(parts[2].replaceAll("[^0-9]", ""));
                }
                if (major == 1) return minor + 1;
                if (minor >= 10) return major * 100 + minor + patch;
                return major * 100 + minor * 10 + patch;
            }
            return Integer.parseInt(clean.replaceAll("[^0-9]", ""));
        } catch (Exception ignored) {
            return 0;
        }
    }

    static File download(Context context, UpdateAsset asset) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(asset.url).openConnection();
        connection.setConnectTimeout(30000);
        connection.setReadTimeout(120000);
        if (connection.getResponseCode() < 200 || connection.getResponseCode() > 299) {
            throw new IllegalStateException("HTTP " + connection.getResponseCode());
        }
        File file = new File(context.getFilesDir(), "update-" + asset.name.replaceAll("[^A-Za-z0-9._-]", "_"));
        try (BufferedInputStream in = new BufferedInputStream(connection.getInputStream());
             FileOutputStream out = new FileOutputStream(file)) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
            }
        }
        return file;
    }
}

class WallpaperStore {
    static void save(Context context, Bitmap bitmap) {
        try {
            File directory = context.getFilesDir();
            File temp = new File(directory, AppConfig.TEMP_WALLPAPER_FILE);
            File file = new File(directory, AppConfig.LAST_WALLPAPER_FILE);
            try (FileOutputStream out = new FileOutputStream(temp)) {
                bitmap.compress(Bitmap.CompressFormat.PNG, 92, out);
            }
            cleanupOldWallpapers(context);
            if (file.exists()) file.delete();
            if (!temp.renameTo(file)) {
                try (FileOutputStream out = new FileOutputStream(file)) {
                    bitmap.compress(Bitmap.CompressFormat.PNG, 92, out);
                }
                temp.delete();
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

    private static void cleanupOldWallpapers(Context context) {
        File[] files = context.getFilesDir().listFiles();
        if (files == null) return;
        for (File file : files) {
            String name = file.getName();
            boolean keep = AppConfig.LAST_WALLPAPER_FILE.equals(name)
                || AppConfig.TEMP_WALLPAPER_FILE.equals(name);
            boolean wallpaper = name.startsWith("wallpaper-")
                || name.startsWith("server-wallpaper-")
                || name.startsWith("generated-wallpaper-")
                || name.startsWith("last_wallpaper_");
            if (!keep && wallpaper) file.delete();
        }
    }
}

class ServerWallpaperClient {
    private static String lastError = "";
    private static boolean lastNotModified = false;

    static boolean isConfigured(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        String base = prefs.getString(AppConfig.KEY_THEME_SERVER_URL, AppConfig.DEFAULT_THEME_SERVER_URL);
        if (base == null || base.trim().isEmpty()) base = AppConfig.DEFAULT_THEME_SERVER_URL;
        return base != null && !base.trim().isEmpty();
    }

    static String lastError() {
        return lastError == null || lastError.isEmpty() ? "Server unavailable." : lastError;
    }

    static boolean lastNotModified() {
        return lastNotModified;
    }

    static Bitmap fetchOrCreate(Context context, WeatherScene scene) {
        try {
            lastError = "";
            lastNotModified = false;
            SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
            String base = prefs.getString(AppConfig.KEY_THEME_SERVER_URL, AppConfig.DEFAULT_THEME_SERVER_URL);
            if (base == null || base.trim().isEmpty()) base = AppConfig.DEFAULT_THEME_SERVER_URL;
            if (base == null || base.trim().isEmpty()) return null;
            String separator = base.contains("?") ? "&" : "?";
            String requestUrl = base.trim()
                + separator + "city=" + enc(scene.cityEnglish)
                + "&cityLocal=" + enc(scene.cityLocal)
                + "&country=" + enc(scene.country)
                + "&date=" + enc(scene.date)
                + "&weather=" + enc(scene.weather)
                + "&period=" + enc(scene.timePeriod)
                + "&character=" + enc(prefs.getString(AppConfig.KEY_CHARACTER, "person"))
                + "&style=" + enc(prefs.getString(AppConfig.KEY_STYLE, "knitted"))
                + "&tempMin=" + scene.tempMin
                + "&tempMax=" + scene.tempMax
                + "&landmarks=" + enc(join(scene.landmarks));
            JSONObject response = new JSONObject(Http.get(new URL(requestUrl), null));
            if (response.has("error")) {
                lastError = response.optString("error", "Server returned an error.");
                return null;
            }
            String fileName = response.optString("file_name", "");
            String imageUrl = response.optString("image_url", "");
            Bitmap bitmap = null;
            if (!imageUrl.isEmpty()) {
                byte[] bytes = Http.getBytes(new URL(imageUrl), null);
                bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
            }
            if (bitmap == null) {
                lastError = "Server returned no image.";
                return null;
            }
            WallpaperStore.save(context, bitmap);
            prefs.edit()
                .putString(AppConfig.KEY_LAST_SCENE_KEY, SceneKeys.forContext(context, scene))
                .putString(AppConfig.KEY_LAST_SERVER_FILE, fileName)
                .apply();
            return bitmap;
        } catch (NotModifiedException notModified) {
            lastNotModified = true;
            lastError = "Server has no newer wallpaper. Keeping current wallpaper.";
            return null;
        } catch (Exception error) {
            lastNotModified = false;
            lastError = error.getMessage();
            return null;
        }
    }

    private static String enc(String value) throws Exception {
        return URLEncoder.encode(value == null ? "" : value, "UTF-8");
    }

    private static String join(List<String> values) {
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) builder.append("|");
            builder.append(values.get(i));
        }
        return builder.toString();
    }
}

class SceneResolver {
    static WeatherScene resolve(Context context) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        if (prefs.getBoolean(AppConfig.KEY_USE_CUSTOM, false)) {
            CityInfo city = CityDatabase.forName(prefs.getString(AppConfig.KEY_CUSTOM_CITY, "Kaohsiung"));
            return applyLanguage(context, SceneFactory.create(city, fetchWeather(context, city.latitude, city.longitude)));
        }

        Location location = findBestLocation(context);
        CityInfo city = reverseGeocode(context, location);
        return applyLanguage(context, SceneFactory.create(city, fetchWeather(context, location.getLatitude(), location.getLongitude())));
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
        String country = normalizeCountry(address);
        String cityLocal = "Kaohsiung";
        if (address != null) {
            if ("Taiwan".equals(country)) {
                if (address.getAdminArea() != null) cityLocal = address.getAdminArea();
                else if (address.getSubAdminArea() != null) cityLocal = address.getSubAdminArea();
                else if (address.getLocality() != null) cityLocal = address.getLocality();
            } else {
                if (address.getLocality() != null) cityLocal = address.getLocality();
                else if (address.getSubAdminArea() != null) cityLocal = address.getSubAdminArea();
                else if (address.getAdminArea() != null) cityLocal = address.getAdminArea();
            }
        }
        return new CityInfo(cityLocal, EnglishCityNames.toEnglish(cityLocal), country, location.getLatitude(), location.getLongitude());
    }

    private static String normalizeCountry(Address address) {
        if (address == null) return "Taiwan";
        String code = address.getCountryCode();
        String name = address.getCountryName();
        if ("TW".equalsIgnoreCase(code) || "Taiwan".equalsIgnoreCase(name) || "台灣".equals(name) || "臺灣".equals(name)) {
            return "Taiwan";
        }
        return name != null && !name.trim().isEmpty() ? name : "Taiwan";
    }

    static WeatherInfo fetchWeather(Context context, double lat, double lon) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        String backend = prefs.getString(AppConfig.KEY_WEATHER_BACKEND_URL, "");
        if (backend == null || backend.trim().isEmpty()) {
            backend = prefs.getString(AppConfig.KEY_THEME_SERVER_URL, AppConfig.DEFAULT_THEME_SERVER_URL);
        }
        if (backend == null || backend.trim().isEmpty()) backend = AppConfig.DEFAULT_THEME_SERVER_URL;
        if (backend == null || backend.trim().isEmpty()) return new WeatherInfo("Cloudy", 27, 32);
        String separator = backend.contains("?") ? "&" : "?";
        URL url = new URL(backend.trim() + separator + "lat=" + lat + "&lon=" + lon + "&units=metric");
        JSONObject root = new JSONObject(Http.get(url, null));
        JSONObject main = root.has("main") ? root.getJSONObject("main") : root;
        Object weatherValue = root.opt("weather");
        String weatherMain;
        if (weatherValue instanceof org.json.JSONArray) {
            weatherMain = ((org.json.JSONArray) weatherValue).getJSONObject(0).getString("main");
        } else if (weatherValue instanceof String) {
            weatherMain = (String) weatherValue;
        } else {
            weatherMain = "Clouds";
        }
        return new WeatherInfo(
            WeatherMapper.normalize(weatherMain),
            (int) Math.round(main.optDouble("temp_min", main.optDouble("tempMin", 27))),
            (int) Math.round(main.optDouble("temp_max", main.optDouble("tempMax", 32)))
        );
    }

    private static WeatherScene applyLanguage(Context context, WeatherScene scene) {
        SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        String language = prefs.getBoolean(AppConfig.KEY_USE_CUSTOM_LANGUAGE, false)
            ? prefs.getString(AppConfig.KEY_CUSTOM_LANGUAGE, scene.language)
            : LanguageRules.forSystem(context);
        if (language == null || language.trim().isEmpty()) language = scene.language;
        return scene.withLanguage(language.trim());
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

    String sceneKey() {
        return cityEnglish + "|" + country + "|" + date + "|" + weather + "|" + timePeriod;
    }

    WeatherScene withLanguage(String value) {
        return new WeatherScene(cityLocal, cityEnglish, country, date, time, weather,
            tempMin, tempMax, timePeriod, landmarks, value);
    }
}

class SceneKeys {
    static String forContext(Context context, WeatherScene scene) {
        SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        String character = prefs.getString(AppConfig.KEY_CHARACTER, "person");
        String style = prefs.getString(AppConfig.KEY_STYLE, "knitted");
        return scene.sceneKey() + "|" + character + "|" + style;
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
        TIME.put("sunraise", "pale dawn light");
        TIME.put("Morning", "soft sunrise");
        TIME.put("Afternoon", "mellow warm afternoon light");
        TIME.put("Sunset", "orange pink sky");
        TIME.put("Night", "warm street lights");
        TIME.put("Midnight", "deep blue quiet sky");
    }

    static String getTimePeriod(int hour) {
        if (hour >= 5 && hour <= 6) return "sunraise";
        if (hour >= 7 && hour <= 11) return "Morning";
        if (hour >= 12 && hour <= 16) return "Afternoon";
        if (hour >= 17 && hour <= 18) return "Sunset";
        if (hour >= 19 && hour <= 23) return "Night";
        return "Midnight";
    }

    static long nextPeriodCheckDelayMillis() {
        LocalTime now = LocalTime.now();
        int nowSeconds = now.getHour() * 3600 + now.getMinute() * 60 + now.getSecond();
        int[] starts = new int[] {0, 5 * 3600, 7 * 3600, 12 * 3600, 17 * 3600, 19 * 3600};
        int next = 24 * 3600;
        for (int start : starts) {
            if (start > nowSeconds) {
                next = start;
                break;
            }
        }
        return Math.max(60L * 1000L, (long) (next - nowSeconds + 10) * 1000L);
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
        if ("Midnight".equals(period) || "Night".equals(period)) return "Ivory White";
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

    static boolean isSunny(String value) {
        return "Sunny".equals(value) || "\u6674".equals(value);
    }

    static boolean isRainy(String value) {
        return "Rainy".equals(value) || hasAny(value, '\u96e8');
    }

    static boolean isSnowy(String value) {
        return "Snowy".equals(value) || hasAny(value, '\u96ea');
    }

    static boolean isCloudy(String value) {
        return "Cloudy".equals(value) || hasAny(value, '\u4e91', '\u9670');
    }

    static boolean isFoggy(String value) {
        return "Foggy".equals(value) || hasAny(value, '\u96fe', '\u973e', '\u5c18', '\u6c99');
    }

    private static boolean hasAny(String value, char... chars) {
        if (value == null) return false;
        for (char item : chars) {
            if (value.indexOf(item) >= 0) return true;
        }
        return false;
    }
}

class CityDatabase {
    private static final Map<String, CityInfo> DATA = new HashMap<>();

    static {
        DATA.put("taipei", new CityInfo("Taipei", "Taipei", "Taiwan", 25.0330, 121.5654));
        DATA.put("台北市", new CityInfo("台北市", "Taipei", "Taiwan", 25.0330, 121.5654));
        DATA.put("臺北市", new CityInfo("臺北市", "Taipei", "Taiwan", 25.0330, 121.5654));
        DATA.put("kaohsiung", new CityInfo("Kaohsiung", "Kaohsiung", "Taiwan", 22.6273, 120.3014));
        DATA.put("高雄市", new CityInfo("高雄市", "Kaohsiung", "Taiwan", 22.6273, 120.3014));
        DATA.put("臺中市", new CityInfo("臺中市", "Taichung", "Taiwan", 24.1477, 120.6736));
        DATA.put("台中市", new CityInfo("台中市", "Taichung", "Taiwan", 24.1477, 120.6736));
        DATA.put("台南市", new CityInfo("台南市", "Tainan", "Taiwan", 22.9999, 120.2269));
        DATA.put("臺南市", new CityInfo("臺南市", "Tainan", "Taiwan", 22.9999, 120.2269));
        DATA.put("新北市", new CityInfo("新北市", "New Taipei", "Taiwan", 25.0169, 121.4628));
        DATA.put("桃園市", new CityInfo("桃園市", "Taoyuan", "Taiwan", 24.9937, 121.3010));
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
        DATA.put("Kaohsiung", Arrays.asList(
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
        ));
        DATA.put("New Taipei", Arrays.asList("Tamsui Old Street", "Jiufen", "Bitan"));
        DATA.put("Taoyuan", Arrays.asList("Daxi Old Street", "Shimen Reservoir", "Xpark"));
        DATA.put("Taichung", Arrays.asList("National Taichung Theater", "Miyahara", "Fengjia Night Market"));
        DATA.put("Tainan", Arrays.asList("Chihkan Tower", "Anping Old Fort", "Shennong Street"));
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

    static String forSystem(Context context) {
        Locale locale;
        if (Build.VERSION.SDK_INT >= 24) {
            locale = context.getResources().getConfiguration().getLocales().get(0);
        } else {
            locale = context.getResources().getConfiguration().locale;
        }
        String language = locale.getLanguage();
        String country = locale.getCountry();
        if ("zh".equals(language) && ("TW".equals(country) || "HK".equals(country) || "MO".equals(country))) {
            return "Traditional Chinese";
        }
        if ("zh".equals(language)) return "Simplified Chinese";
        if ("ja".equals(language)) return "Japanese";
        if ("ko".equals(language)) return "Korean";
        if ("fr".equals(language)) return "French";
        if ("de".equals(language)) return "German";
        return "English";
    }
}

class EnglishCityNames {
    private static final Map<String, String> DATA = new HashMap<>();

    static {
        DATA.put("Taipei", "Taipei");
        DATA.put("Taipei City", "Taipei");
        DATA.put("台北市", "Taipei");
        DATA.put("臺北市", "Taipei");
        DATA.put("Kaohsiung", "Kaohsiung");
        DATA.put("Kaohsiung City", "Kaohsiung");
        DATA.put("高雄市", "Kaohsiung");
        DATA.put("台中市", "Taichung");
        DATA.put("臺中市", "Taichung");
        DATA.put("台南市", "Tainan");
        DATA.put("臺南市", "Tainan");
        DATA.put("新北市", "New Taipei");
        DATA.put("桃園市", "Taoyuan");
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
            + "Keep the upper sky area light, calm, open, and visually clean so phone time, date, and status widgets do not conflict.\n\n"
            + "Do not write the city name anywhere in the image. Do not place a large title, header text, or location label in the sky.\n\n"
            + "Do not draw phone UI, clock, date, temperature text, status bar, widgets, or app labels.\n\n"
            + "Leave enough upper blank space so the Android lock screen can show its built-in clock and date without conflict.\n\n"
            + "Crochet " + scene.weather.toLowerCase(Locale.US) + " weather icon.\n\n"
            + "No large readable headline text.\n\n"
            + "9:16 portrait wallpaper.";
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

    static byte[] getBytes(URL url, Map<String, String> headers) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(30000);
        connection.setReadTimeout(120000);
        if (headers != null) for (Map.Entry<String, String> entry : headers.entrySet()) {
            connection.setRequestProperty(entry.getKey(), entry.getValue());
        }
        int code = connection.getResponseCode();
        if (code < 200 || code > 299) {
            throw new IllegalStateException("HTTP " + code);
        }
        try (BufferedInputStream input = new BufferedInputStream(connection.getInputStream());
             java.io.ByteArrayOutputStream output = new java.io.ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
            return output.toByteArray();
        }
    }

    static String read(HttpURLConnection connection) throws Exception {
        int code = connection.getResponseCode();
        if (code == 304) {
            throw new NotModifiedException();
        }
        BufferedReader reader = new BufferedReader(new InputStreamReader(
            code >= 200 && code <= 299
                ? connection.getInputStream()
                : connection.getErrorStream()
        ));
        StringBuilder builder = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) builder.append(line);
        String body = builder.toString();
        if (code < 200 || code > 299) {
            throw new IllegalStateException("HTTP " + code + ": " + body);
        }
        return body;
    }
}

class NotModifiedException extends Exception {
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

    static void drawLoadingFrame(Canvas canvas, int width, int height, WeatherScene scene, long frame) {
        drawBackground(canvas, width, height, scene);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setTextAlign(Paint.Align.CENTER);
        paint.setTextSize(Math.max(34f, width * 0.042f));
        paint.setColor(textPaintColor(scene));
        paint.setShadowLayer(8f, 0f, 2f, Color.argb(110, 38, 30, 24));
        canvas.drawText("Downloading latest wallpaper...", width * 0.50f, height * 0.22f, paint);
        drawWeatherOverlay(canvas, width, height, scene, frame);
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
            case "sunraise":
                start = Color.rgb(255, 218, 178);
                end = Color.rgb(184, 220, 230);
                break;
            case "Sunset":
                start = Color.rgb(237, 126, 92);
                end = Color.rgb(255, 196, 150);
                break;
            case "Midnight":
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
            if ("Night".equals(scene.timePeriod) || "Midnight".equals(scene.timePeriod)) {
                drawWindows(canvas, rect, frame + i * 9);
            }
        }

        paint.setColor(Color.rgb(82, 67, 57));
        canvas.drawRoundRect(new RectF(width * 0.44f, ground - 520f, width * 0.56f, ground + 34f), 24f, 24f, paint);
        paint.setColor(Color.rgb(230, 215, 188));
        canvas.drawCircle(width * 0.50f, ground - 560f, 54f, paint);
        drawPeople(canvas, height, frame);
    }

    static void drawCityLabelOverlay(Canvas canvas, int width, int height, WeatherScene scene) {
    }

    private static int textPaintColor(WeatherScene scene) {
        if ("Midnight".equals(scene.timePeriod) || "Rainy".equals(scene.weather)) {
            return Color.rgb(255, 247, 224);
        }
        if ("Sunset".equals(scene.timePeriod)) {
            return Color.rgb(113, 55, 25);
        }
        if ("Sunny".equals(scene.weather)) {
            return Color.rgb(93, 58, 39);
        }
        return Color.rgb(58, 58, 58);
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
        drawLiveMotionOverlay(canvas, width, height, scene, frame);
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

    private static void drawLiveMotionOverlay(Canvas canvas, int width, int height, WeatherScene scene, long frame) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        float cloudDrift = (frame * 1.7f) % (width + 360f);
        paint.setColor(Color.argb("Midnight".equals(scene.timePeriod) ? 70 : 90, 255, 250, 232));
        for (int i = 0; i < 4; i++) {
            float x = -260f + ((cloudDrift + i * width * 0.36f) % (width + 420f));
            float y = height * (0.18f + i * 0.055f);
            drawSoftCloud(canvas, x, y, width * 0.18f, paint);
        }

        for (int i = 0; i < 20; i++) {
            int pulse = (int) ((frame * 5 + i * 23) % 160);
            int alpha = 55 + Math.abs(80 - pulse);
            paint.setColor(Color.argb(alpha, 255, 222, 142));
            float x = (i * 73 + (frame % 220) * 0.55f) % width;
            float y = height * 0.36f + ((i * 97) % (int) (height * 0.44f));
            canvas.drawCircle(x, y, 4f + (i % 3) * 2f, paint);
        }

        if ("Midnight".equals(scene.timePeriod) || "Night".equals(scene.timePeriod) || "Sunset".equals(scene.timePeriod)) {
            for (int i = 0; i < 14; i++) {
                int alpha = ((frame + i * 11) % 48) < 24 ? 180 : 85;
                paint.setColor(Color.argb(alpha, 255, 202, 102));
                float x = width * (0.08f + (i % 7) * 0.14f);
                float y = height * (0.55f + (i / 7) * 0.12f);
                canvas.drawCircle(x, y, 8f, paint);
            }
        }

        if ("Sunny".equals(scene.weather)) {
            paint.setColor(Color.argb(75, 255, 218, 105));
            float glow = 44f + (frame % 60);
            canvas.drawCircle(width * 0.82f, height * 0.17f, glow, paint);
        }
        if ("Snowy".equals(scene.weather)) {
            paint.setColor(Color.argb(170, 255, 255, 255));
            for (int i = 0; i < 36; i++) {
                float x = (i * 47 + frame * 2) % width;
                float y = height * 0.16f + ((i * 83 + frame * 5) % (int) (height * 0.74f));
                canvas.drawCircle(x, y, 7f, paint);
            }
        }
    }

    private static void drawSoftCloud(Canvas canvas, float x, float y, float radius, Paint paint) {
        canvas.drawOval(new RectF(x, y, x + radius * 1.7f, y + radius * 0.55f), paint);
        canvas.drawOval(new RectF(x + radius * 0.42f, y - radius * 0.18f, x + radius * 1.32f, y + radius * 0.50f), paint);
        canvas.drawOval(new RectF(x + radius, y + radius * 0.02f, x + radius * 2.18f, y + radius * 0.58f), paint);
    }
}
