package com.codex.amigurumiweather;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.app.WallpaperManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.os.Build;
import android.os.SystemClock;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class WallpaperSyncReceiver extends BroadcastReceiver {
    static final String ACTION_SYNC = "com.codex.amigurumiweather.SYNC_WALLPAPER";
    private static final long SYNC_INTERVAL_MS = 60L * 60L * 1000L;

    @Override
    public void onReceive(Context context, Intent intent) {
        schedule(context);
        if (intent != null && Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            return;
        }

        final PendingResult pending = goAsync();
        ExecutorService executor = Executors.newSingleThreadExecutor();
        executor.execute(() -> {
            try {
                syncNow(context.getApplicationContext());
            } finally {
                pending.finish();
                executor.shutdown();
            }
        });
    }

    static void schedule(Context context) {
        AlarmManager alarm = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarm == null) return;
        PendingIntent pending = pendingIntent(context);
        long firstRun = SystemClock.elapsedRealtime() + SYNC_INTERVAL_MS;
        alarm.cancel(pending);
        alarm.setInexactRepeating(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            firstRun,
            SYNC_INTERVAL_MS,
            pending
        );
    }

    static void syncNow(Context context) {
        try {
            WeatherScene scene = SceneResolver.resolve(context);
            Bitmap bitmap = ServerWallpaperClient.fetchOrCreate(context, scene);
            if (bitmap == null) return;

            SharedPreferences prefs = context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
            boolean dynamicEnabled = prefs.getBoolean(AppConfig.KEY_DYNAMIC_ENABLED, false);
            prefs.edit()
                .putLong(AppConfig.KEY_LAST_SYNC_MS, System.currentTimeMillis())
                .putString(AppConfig.KEY_LAST_SCENE_KEY, SceneKeys.forContext(context, scene))
                .apply();

            if (!dynamicEnabled) {
                WallpaperManager.getInstance(context).setBitmap(bitmap);
            }
        } catch (Exception ignored) {
            // Background sync must never crash the phone process. The foreground app shows detailed status.
        }
    }

    private static PendingIntent pendingIntent(Context context) {
        Intent intent = new Intent(context, WallpaperSyncReceiver.class);
        intent.setAction(ACTION_SYNC);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        return PendingIntent.getBroadcast(context, 3301, intent, flags);
    }
}
