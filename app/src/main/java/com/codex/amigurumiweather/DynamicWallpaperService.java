package com.codex.amigurumiweather;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Rect;
import android.os.Handler;
import android.service.wallpaper.WallpaperService;
import android.view.SurfaceHolder;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class DynamicWallpaperService extends WallpaperService {
    @Override
    public Engine onCreateEngine() {
        return new AmigurumiEngine();
    }

    private class AmigurumiEngine extends Engine {
        private final Handler handler = new Handler();
        private final ExecutorService executor = Executors.newSingleThreadExecutor();
        private boolean visible;
        private WeatherScene scene = SceneFactory.createFallback();
        private Bitmap background;
        private long frame;
        private long lastRefresh;

        private final Runnable drawRunnable = new Runnable() {
            @Override
            public void run() {
                draw();
            }
        };

        @Override
        public void onVisibilityChanged(boolean visible) {
            this.visible = visible;
            if (visible) {
                getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE)
                    .edit()
                    .putString(AppConfig.KEY_WALLPAPER_MODE, AppConfig.WALLPAPER_MODE_DYNAMIC)
                    .apply();
                refreshSceneIfNeeded(true);
                draw();
            } else {
                handler.removeCallbacks(drawRunnable);
            }
        }

        @Override
        public void onSurfaceChanged(SurfaceHolder holder, int format, int width, int height) {
            super.onSurfaceChanged(holder, format, width, height);
            draw();
        }

        @Override
        public void onSurfaceDestroyed(SurfaceHolder holder) {
            super.onSurfaceDestroyed(holder);
            visible = false;
            handler.removeCallbacks(drawRunnable);
        }

        @Override
        public void onDestroy() {
            super.onDestroy();
            handler.removeCallbacks(drawRunnable);
            executor.shutdownNow();
        }

        private void draw() {
            SurfaceHolder holder = getSurfaceHolder();
            Canvas canvas = null;
            try {
                canvas = holder.lockCanvas();
                if (canvas != null) {
                    int width = canvas.getWidth();
                    int height = canvas.getHeight();
                    if (background != null) {
                        drawCover(canvas, background, width, height);
                        LocalWallpaperRenderer.drawWeatherOverlay(canvas, width, height, scene, frame++);
                    } else {
                        LocalWallpaperRenderer.drawLoadingFrame(canvas, width, height, scene, frame++);
                    }
                }
            } finally {
                if (canvas != null) holder.unlockCanvasAndPost(canvas);
            }

            refreshSceneIfNeeded(false);
            handler.removeCallbacks(drawRunnable);
            if (visible) handler.postDelayed(drawRunnable, 66);
        }

        private void refreshSceneIfNeeded(boolean force) {
            long now = System.currentTimeMillis();
            SharedPreferences prefs = getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
            long interval = background == null ? 30L * 1000L : Rules.nextPeriodCheckDelayMillis();
            if (!force && now - lastRefresh < interval) return;
            lastRefresh = now;

            executor.execute(() -> {
                try {
                    WeatherScene next = SceneResolver.resolve(DynamicWallpaperService.this);
                    String oldKey = prefs.getString(AppConfig.KEY_LAST_SCENE_KEY, "");
                    String newKey = SceneKeys.forContext(DynamicWallpaperService.this, next);
                    Bitmap latest = WallpaperStore.load(DynamicWallpaperService.this);
                    if (background == null && latest != null) background = latest;
                    scene = next;
                    if (!newKey.equals(oldKey) || background == null) {
                        Bitmap generated = fetchRequiredWallpaper(next);
                        if (generated != null) {
                            background = generated;
                            WallpaperStore.save(DynamicWallpaperService.this, generated);
                            prefs.edit().putString(AppConfig.KEY_LAST_SCENE_KEY, newKey).apply();
                        } else if (background == null) {
                            background = LocalWallpaperRenderer.render(next);
                        }
                    } else if (ServerWallpaperClient.isConfigured(DynamicWallpaperService.this)) {
                        Bitmap server = ServerWallpaperClient.fetchOrCreate(DynamicWallpaperService.this, next);
                        if (server != null) background = server;
                    }
                } catch (Exception ignored) {
                    scene = SceneFactory.createFallback();
                    Bitmap latest = WallpaperStore.load(DynamicWallpaperService.this);
                    if (latest != null) background = latest;
                    if (background == null) background = LocalWallpaperRenderer.render(scene);
                }
            });
        }

        private Bitmap fetchRequiredWallpaper(WeatherScene next) {
            Bitmap server = ServerWallpaperClient.fetchOrCreate(DynamicWallpaperService.this, next);
            if (server != null) return server;
            if (ServerWallpaperClient.isConfigured(DynamicWallpaperService.this)) {
                Bitmap cached = WallpaperStore.load(DynamicWallpaperService.this);
                return cached != null ? cached : LocalWallpaperRenderer.render(next);
            }
            return LocalWallpaperRenderer.render(next);
        }

        private void drawCover(Canvas canvas, Bitmap bitmap, int width, int height) {
            float sourceRatio = bitmap.getWidth() / (float) bitmap.getHeight();
            float targetRatio = width / (float) height;
            Rect src;
            if (sourceRatio > targetRatio) {
                int srcWidth = Math.round(bitmap.getHeight() * targetRatio);
                int left = (bitmap.getWidth() - srcWidth) / 2;
                src = new Rect(left, 0, left + srcWidth, bitmap.getHeight());
            } else {
                int srcHeight = Math.round(bitmap.getWidth() / targetRatio);
                int top = (bitmap.getHeight() - srcHeight) / 2;
                src = new Rect(0, top, bitmap.getWidth(), top + srcHeight);
            }
            canvas.drawBitmap(bitmap, src, new Rect(0, 0, width, height), new Paint(Paint.FILTER_BITMAP_FLAG));
        }
    }
}
