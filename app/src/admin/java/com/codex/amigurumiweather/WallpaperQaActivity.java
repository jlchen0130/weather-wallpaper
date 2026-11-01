package com.codex.amigurumiweather;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.view.WindowManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Admin-only QA mode: fetch one exact R2 key through the Worker, or walk every
 * expected key (festival combinations first) and write a CSV report.
 */
public class WallpaperQaActivity extends Activity {
    private static final int REQUEST_EXPORT_CSV = 3101;
    private static final String KEY_QA_SERVER_URL = "qa_server_url";
    private static final String[] SCOPES = {"全部（節慶優先）", "只節慶", "只一般天氣"};

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ExecutorService singleExecutor = Executors.newSingleThreadExecutor();
    private volatile boolean batchRunning = false;
    private volatile boolean batchCancel = false;
    private SharedPreferences prefs;
    private List<WallpaperQaRules.Target> targets = new ArrayList<>();
    private File lastReport;

    private EditText serverUrl;
    private Spinner citySpinner;
    private Spinner festivalSpinner;
    private Spinner periodSpinner;
    private Spinner weatherSpinner;
    private TextView singleResult;
    private ImageView preview;
    private Spinner scopeSpinner;
    private Spinner batchCitySpinner;
    private Button batchStart;
    private Button batchStop;
    private Button exportCsv;
    private TextView batchStatus;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
        setContentView(buildUi());
        try (InputStream input = getAssets().open(WallpaperQaRules.MANIFEST_ASSET)) {
            targets = WallpaperQaRules.readManifest(input);
            batchStatus.setText("巡檢清單：" + targets.size() + " 個 key");
        } catch (Exception error) {
            batchStatus.setText("無法讀取巡檢清單：" + error.getMessage());
            batchStart.setEnabled(false);
        }
    }

    @Override
    protected void onDestroy() {
        batchCancel = true;
        executor.shutdownNow();
        singleExecutor.shutdownNow();
        super.onDestroy();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(28));
        root.setBackgroundColor(Color.rgb(255, 248, 239));

        root.addView(heading("Wallpaper QA 測試模式", 22f));
        root.addView(label("Worker 網址"));
        serverUrl = new EditText(this);
        serverUrl.setSingleLine(true);
        serverUrl.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        serverUrl.setText(prefs.getString(KEY_QA_SERVER_URL,
            prefs.getString(AppConfig.KEY_THEME_SERVER_URL, AppConfig.DEFAULT_THEME_SERVER_URL)));
        root.addView(serverUrl);

        root.addView(heading("單張取圖", 18f));
        root.addView(label("城市"));
        citySpinner = spinner(WallpaperQaRules.CITIES, "Kaohsiung");
        root.addView(citySpinner);
        root.addView(label("節日"));
        festivalSpinner = spinner(WallpaperQaRules.FESTIVALS, "none");
        root.addView(festivalSpinner);
        root.addView(label("時段（非晴／晴時多雲時一律 all_day）"));
        periodSpinner = spinner(WallpaperQaRules.PERIODS, "afternoon");
        root.addView(periodSpinner);
        root.addView(label("天氣"));
        weatherSpinner = spinner(WallpaperQaRules.WEATHERS, "sunny");
        root.addView(weatherSpinner);

        Button fetch = new Button(this);
        fetch.setText("立即取圖");
        fetch.setOnClickListener(v -> fetchSingle());
        root.addView(fetch, fullWidth(dp(48)));

        singleResult = text("尚未取圖", 13f);
        singleResult.setTextIsSelectable(true);
        root.addView(singleResult);

        preview = new ImageView(this);
        preview.setBackgroundColor(Color.rgb(241, 224, 204));
        preview.setAdjustViewBounds(true);
        preview.setScaleType(ImageView.ScaleType.FIT_CENTER);
        root.addView(preview, fullWidth(dp(480)));

        root.addView(heading("批次巡檢", 18f));
        root.addView(label("範圍"));
        scopeSpinner = spinner(SCOPES, SCOPES[0]);
        root.addView(scopeSpinner);
        root.addView(label("城市"));
        String[] batchCities = new String[WallpaperQaRules.CITIES.length + 1];
        batchCities[0] = "全部城市";
        System.arraycopy(WallpaperQaRules.CITIES, 0, batchCities, 1, WallpaperQaRules.CITIES.length);
        batchCitySpinner = spinner(batchCities, batchCities[0]);
        root.addView(batchCitySpinner);

        batchStart = new Button(this);
        batchStart.setText("開始批次巡檢");
        batchStart.setOnClickListener(v -> startBatch());
        root.addView(batchStart, fullWidth(dp(48)));

        batchStop = new Button(this);
        batchStop.setText("停止");
        batchStop.setEnabled(false);
        batchStop.setOnClickListener(v -> batchCancel = true);
        root.addView(batchStop, fullWidth(dp(48)));

        exportCsv = new Button(this);
        exportCsv.setText("匯出 CSV 報告");
        exportCsv.setEnabled(false);
        exportCsv.setOnClickListener(v -> exportReport());
        root.addView(exportCsv, fullWidth(dp(48)));

        batchStatus = text("", 13f);
        batchStatus.setTextIsSelectable(true);
        root.addView(batchStatus);

        TextView version = text("Admin APK 版本：" + AppVersion.currentName(this), 12f);
        version.setPadding(0, dp(12), 0, 0);
        root.addView(version);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        return scroll;
    }

    private String baseUrl() {
        String base = serverUrl.getText().toString().trim();
        if (base.isEmpty()) base = AppConfig.DEFAULT_THEME_SERVER_URL;
        prefs.edit().putString(KEY_QA_SERVER_URL, base).apply();
        return base;
    }

    private void fetchSingle() {
        String city = citySpinner.getSelectedItem().toString();
        String festival = festivalSpinner.getSelectedItem().toString();
        String period = periodSpinner.getSelectedItem().toString();
        String weather = weatherSpinner.getSelectedItem().toString();
        String key = WallpaperQaRules.key(festival, city, period, weather);
        boolean inRules = WallpaperQaRules.find(targets, key) != null;
        String base = baseUrl();
        singleResult.setText("取圖中…\n" + key);
        preview.setImageDrawable(null);
        singleExecutor.execute(() -> {
            WallpaperQaRules.Probe probe = WallpaperQaRules.probe(base, key, true);
            Bitmap bitmap = "hit".equals(probe.result) ? decodePreview(probe) : null;
            probe.body = null;
            StringBuilder message = new StringBuilder()
                .append("結果：").append(probe.result).append('\n')
                .append("HTTP 狀態：").append(probe.status == 0 ? "-" : String.valueOf(probe.status)).append('\n')
                .append("R2 key：").append(key).append('\n')
                .append("讀取時間：").append(probe.ms).append(" ms\n")
                .append("位元組數：").append(probe.bytes).append('\n')
                .append("圖片尺寸：").append(probe.width == 0 ? "-" : probe.width + " × " + probe.height).append('\n')
                .append("素材規則內：").append(inRules ? "是" : "否（此組合不在巡檢清單）");
            if (!probe.error.isEmpty()) message.append("\n錯誤：").append(probe.error);
            runOnUiThread(() -> {
                singleResult.setText(message.toString());
                preview.setImageBitmap(bitmap);
            });
        });
    }

    private Bitmap decodePreview(WallpaperQaRules.Probe probe) {
        if (probe.body == null) return null;
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inSampleSize = 1;
        while (probe.width / (options.inSampleSize * 2) >= 540) options.inSampleSize *= 2;
        return BitmapFactory.decodeByteArray(probe.body, 0, probe.body.length, options);
    }

    private List<WallpaperQaRules.Target> selectedTargets() {
        int scope = scopeSpinner.getSelectedItemPosition();
        int cityIndex = batchCitySpinner.getSelectedItemPosition();
        String city = cityIndex <= 0 ? null : WallpaperQaRules.CITIES[cityIndex - 1];
        List<WallpaperQaRules.Target> chosen = new ArrayList<>();
        for (WallpaperQaRules.Target target : targets) {
            boolean festival = !"none".equals(target.festival);
            if (scope == 1 && !festival) continue;
            if (scope == 2 && festival) continue;
            if (city != null && !city.equals(target.city)) continue;
            chosen.add(target);
        }
        return chosen;
    }

    private void startBatch() {
        if (batchRunning) return;
        List<WallpaperQaRules.Target> chosen = selectedTargets();
        if (chosen.isEmpty()) {
            batchStatus.setText("沒有符合條件的 key");
            return;
        }
        File directory = getExternalFilesDir("qa");
        if (directory == null) directory = new File(getFilesDir(), "qa");
        directory.mkdirs();
        String stamp = new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(new Date());
        File report = new File(directory, "wallpaper_audit_" + stamp + ".csv");
        String base = baseUrl();

        batchRunning = true;
        batchCancel = false;
        batchStart.setEnabled(false);
        batchStop.setEnabled(true);
        exportCsv.setEnabled(false);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        batchStatus.setText("開始巡檢 " + chosen.size() + " 個 key…");

        executor.execute(() -> {
            int hit = 0;
            int missing = 0;
            int failed = 0;
            int done = 0;
            String failure = "";
            List<String> missingKeys = new ArrayList<>();
            try (Writer writer = new OutputStreamWriter(new FileOutputStream(report), StandardCharsets.UTF_8)) {
                writer.write(WallpaperQaRules.csvHeader());
                for (WallpaperQaRules.Target target : chosen) {
                    if (batchCancel) break;
                    WallpaperQaRules.Probe probe = WallpaperQaRules.probe(base, target.key, false);
                    writer.write(WallpaperQaRules.csvRow(target, probe));
                    writer.flush();
                    done++;
                    if ("hit".equals(probe.result)) {
                        hit++;
                    } else {
                        if ("missing".equals(probe.result)) missing++;
                        else failed++;
                        missingKeys.add(probe.result + " " + target.key);
                    }
                    if (done % 10 == 0 || done == chosen.size()) {
                        String progress = done + "/" + chosen.size() + "　命中 " + hit + "　缺圖 " + missing
                            + "　錯誤 " + failed + "\n目前：" + target.key;
                        runOnUiThread(() -> batchStatus.setText(progress));
                    }
                }
            } catch (Exception error) {
                failure = "\n寫入報告失敗：" + error.getMessage();
            }
            StringBuilder summary = new StringBuilder()
                .append(batchCancel ? "已停止" : "完成").append("：").append(done).append("/").append(chosen.size())
                .append("　命中 ").append(hit).append("　缺圖 ").append(missing).append("　錯誤 ").append(failed)
                .append("\n報告：").append(report.getAbsolutePath()).append(failure);
            int shown = Math.min(missingKeys.size(), 200);
            if (shown > 0) summary.append("\n\n缺圖／錯誤（前 ").append(shown).append(" 筆）：");
            for (int i = 0; i < shown; i++) summary.append('\n').append(missingKeys.get(i));
            runOnUiThread(() -> {
                batchRunning = false;
                lastReport = report;
                batchStatus.setText(summary.toString());
                batchStart.setEnabled(true);
                batchStop.setEnabled(false);
                exportCsv.setEnabled(true);
                getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            });
        });
    }

    private void exportReport() {
        if (lastReport == null || !lastReport.exists()) return;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("text/csv");
        intent.putExtra(Intent.EXTRA_TITLE, lastReport.getName());
        startActivityForResult(intent, REQUEST_EXPORT_CSV);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_EXPORT_CSV || resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;
        }
        Uri target = data.getData();
        File source = lastReport;
        executor.execute(() -> {
            String message;
            try (InputStream input = new FileInputStream(source);
                 OutputStream output = getContentResolver().openOutputStream(target)) {
                byte[] buffer = new byte[8192];
                int read;
                while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
                message = "\n已匯出：" + target;
            } catch (Exception error) {
                message = "\n匯出失敗：" + error.getMessage();
            }
            String finalMessage = message;
            runOnUiThread(() -> batchStatus.append(finalMessage));
        });
    }

    private Spinner spinner(String[] values, String selected) {
        Spinner spinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, values);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(adapter);
        for (int i = 0; i < values.length; i++) {
            if (values[i].equals(selected)) spinner.setSelection(i);
        }
        return spinner;
    }

    private TextView heading(String value, float size) {
        TextView view = text(value, size);
        view.setTypeface(Typeface.DEFAULT_BOLD);
        view.setPadding(0, dp(14), 0, dp(6));
        return view;
    }

    private TextView label(String value) {
        TextView view = text(value, 14f);
        view.setPadding(0, dp(8), 0, 0);
        return view;
    }

    private TextView text(String value, float size) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(Color.rgb(65, 45, 34));
        return view;
    }

    private LinearLayout.LayoutParams fullWidth(int height) {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, height);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
