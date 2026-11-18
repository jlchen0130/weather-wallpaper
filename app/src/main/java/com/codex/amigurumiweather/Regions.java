package com.codex.amigurumiweather;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;

import com.android.billingclient.api.AcknowledgePurchaseParams;
import com.android.billingclient.api.BillingClient;
import com.android.billingclient.api.BillingClientStateListener;
import com.android.billingclient.api.BillingFlowParams;
import com.android.billingclient.api.BillingResult;
import com.android.billingclient.api.PendingPurchasesParams;
import com.android.billingclient.api.ProductDetails;
import com.android.billingclient.api.Purchase;
import com.android.billingclient.api.PurchasesUpdatedListener;
import com.android.billingclient.api.QueryProductDetailsParams;
import com.android.billingclient.api.QueryPurchasesParams;

import java.util.Collections;
import java.util.List;
import java.util.Locale;

/** The 22 Taiwan counties/cities that have wallpapers on R2, keyed by the R2 file-name city. */
final class TaiwanRegions {
    static final class Region {
        final String key;
        final String nameZh;
        final double latitude;
        final double longitude;
        private final String[] aliases;

        Region(String key, String nameZh, double latitude, double longitude, String... aliases) {
            this.key = key;
            this.nameZh = nameZh;
            this.latitude = latitude;
            this.longitude = longitude;
            this.aliases = aliases;
        }

        CityInfo toCityInfo() {
            return new CityInfo(nameZh, key, "Taiwan", latitude, longitude);
        }

        boolean matches(String normalized) {
            if (normalized.equals(normalize(key)) || normalized.equals(normalize(nameZh))) return true;
            for (String alias : aliases) {
                if (normalized.equals(normalize(alias))) return true;
            }
            return false;
        }
    }

    static final Region[] ALL = {
        new Region("Taipei", "台北市", 25.0375, 121.5637, "Taipei City"),
        new Region("NewTaipei", "新北市", 25.0120, 121.4650, "New Taipei", "New Taipei City"),
        new Region("Keelung", "基隆市", 25.1283, 121.7419, "Keelung City"),
        new Region("Taoyuan", "桃園市", 24.9936, 121.3010, "Taoyuan City"),
        new Region("HsinchuCity", "新竹市", 24.8138, 120.9675, "Hsinchu City", "Hsinchu"),
        new Region("HsinchuCounty", "新竹縣", 24.8270, 121.0128, "Hsinchu County"),
        new Region("Miaoli", "苗栗縣", 24.5602, 120.8214, "Miaoli County"),
        new Region("Taichung", "台中市", 24.1477, 120.6736, "Taichung City"),
        new Region("Changhua", "彰化縣", 24.0809, 120.5385, "Changhua County"),
        new Region("Nantou", "南投縣", 23.9097, 120.6837, "Nantou County"),
        new Region("Yunlin", "雲林縣", 23.7092, 120.4313, "Yunlin County"),
        new Region("ChiayiCity", "嘉義市", 23.4801, 120.4491, "Chiayi City", "Chiayi"),
        new Region("ChiayiCounty", "嘉義縣", 23.4588, 120.2930, "Chiayi County"),
        new Region("Tainan", "台南市", 22.9999, 120.2270, "Tainan City"),
        new Region("Kaohsiung", "高雄市", 22.6273, 120.3014, "Kaohsiung City"),
        new Region("Pingtung", "屏東縣", 22.6690, 120.4862, "Pingtung County"),
        new Region("Yilan", "宜蘭縣", 24.7570, 121.7533, "Yilan County"),
        new Region("Hualien", "花蓮縣", 23.9872, 121.6015, "Hualien County"),
        new Region("Taitung", "台東縣", 22.7583, 121.1444, "Taitung County"),
        new Region("Penghu", "澎湖縣", 23.5655, 119.5793, "Penghu County"),
        new Region("Kinmen", "金門縣", 24.4368, 118.3186, "Kinmen County"),
        new Region("Lienchiang", "連江縣", 26.1505, 119.9499, "Lienchiang County", "Matsu", "馬祖")
    };

    private TaiwanRegions() {
    }

    static Region match(String raw) {
        if (raw == null || raw.trim().isEmpty()) return null;
        String normalized = normalize(raw);
        for (Region region : ALL) {
            if (region.matches(normalized)) return region;
        }
        return null;
    }

    static Region byKey(String key) {
        if (key == null) return null;
        for (Region region : ALL) {
            if (region.key.equals(key)) return region;
        }
        return null;
    }

    static int indexOf(String key) {
        for (int i = 0; i < ALL.length; i++) {
            if (ALL[i].key.equals(key)) return i;
        }
        return 0;
    }

    static String[] labels() {
        String[] labels = new String[ALL.length];
        for (int i = 0; i < ALL.length; i++) labels[i] = ALL[i].nameZh;
        return labels;
    }

    private static String normalize(String value) {
        return value.trim().toLowerCase(Locale.US).replace('臺', '台').replaceAll("[\\s_-]+", "");
    }
}

/**
 * Google Play free tier: wallpapers stay on the county/city of the first real GPS fix.
 * Buying unlock_all_regions lifts the lock. Only active in flavors built with REGION_LOCK.
 */
final class RegionLock {
    static final String KEY_UNLOCKED = "regions_unlocked";
    static final String KEY_LOCKED_REGION = "locked_region";

    private RegionLock() {
    }

    static boolean enabled() {
        return BuildConfig.REGION_LOCK;
    }

    static boolean isUnlocked(Context context) {
        return prefs(context).getBoolean(KEY_UNLOCKED, false);
    }

    static boolean isLocked(Context context) {
        return enabled() && !isUnlocked(context);
    }

    static TaiwanRegions.Region lockedRegion(Context context) {
        return TaiwanRegions.byKey(prefs(context).getString(KEY_LOCKED_REGION, null));
    }

    /** Remembers the region of the first real location fix; later fixes never move it. */
    static TaiwanRegions.Region lockFrom(Context context, CityInfo city) {
        TaiwanRegions.Region existing = lockedRegion(context);
        if (existing != null) return existing;
        TaiwanRegions.Region region = TaiwanRegions.match(city.cityLocal);
        if (region == null) region = TaiwanRegions.match(city.cityEnglish);
        if (region != null) prefs(context).edit().putString(KEY_LOCKED_REGION, region.key).apply();
        return region;
    }

    static void setUnlocked(Context context, boolean unlocked) {
        prefs(context).edit().putBoolean(KEY_UNLOCKED, unlocked).apply();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(AppConfig.PREFS, Context.MODE_PRIVATE);
    }
}

/** One-time in-app product that unlocks every region. Restores itself from Play on every start. */
final class PlayBilling implements PurchasesUpdatedListener {
    static final String PRODUCT_ID = "unlock_all_regions";

    interface Listener {
        void onBillingChanged(String message);
    }

    private final Context context;
    private final Listener listener;
    private final BillingClient client;
    private volatile ProductDetails product;

    PlayBilling(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
        this.client = BillingClient.newBuilder(this.context)
            .setListener(this)
            .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
            .enableAutoServiceReconnection()
            .build();
    }

    void start() {
        client.startConnection(new BillingClientStateListener() {
            @Override
            public void onBillingSetupFinished(BillingResult result) {
                if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) return;
                queryProduct();
                refreshPurchases();
            }

            @Override
            public void onBillingServiceDisconnected() {
            }
        });
    }

    void end() {
        client.endConnection();
    }

    String formattedPrice() {
        ProductDetails details = product;
        if (details == null || details.getOneTimePurchaseOfferDetails() == null) return null;
        return details.getOneTimePurchaseOfferDetails().getFormattedPrice();
    }

    boolean launchPurchase(Activity activity) {
        ProductDetails details = product;
        if (details == null) return false;
        BillingFlowParams params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(Collections.singletonList(
                BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(details).build()))
            .build();
        return client.launchBillingFlow(activity, params).getResponseCode() == BillingClient.BillingResponseCode.OK;
    }

    void refreshPurchases() {
        client.queryPurchasesAsync(
            QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.INAPP).build(),
            (result, purchases) -> {
                if (result.getResponseCode() == BillingClient.BillingResponseCode.OK) handle(purchases, true);
            });
    }

    @Override
    public void onPurchasesUpdated(BillingResult result, List<Purchase> purchases) {
        int code = result.getResponseCode();
        if (code == BillingClient.BillingResponseCode.OK && purchases != null) {
            handle(purchases, false);
        } else if (code == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
            refreshPurchases();
        } else if (code != BillingClient.BillingResponseCode.USER_CANCELED) {
            listener.onBillingChanged("購買未完成：" + result.getDebugMessage());
        }
    }

    private void queryProduct() {
        QueryProductDetailsParams params = QueryProductDetailsParams.newBuilder()
            .setProductList(Collections.singletonList(QueryProductDetailsParams.Product.newBuilder()
                .setProductId(PRODUCT_ID)
                .setProductType(BillingClient.ProductType.INAPP)
                .build()))
            .build();
        client.queryProductDetailsAsync(params, (result, details) -> {
            List<ProductDetails> list = details.getProductDetailsList();
            if (result.getResponseCode() == BillingClient.BillingResponseCode.OK && !list.isEmpty()) {
                product = list.get(0);
                listener.onBillingChanged(null);
            }
        });
    }

    /** authoritative = full purchase list from Play, so a missing purchase (refund) re-locks. */
    private void handle(List<Purchase> purchases, boolean authoritative) {
        boolean owned = false;
        boolean pending = false;
        for (Purchase purchase : purchases) {
            if (!purchase.getProducts().contains(PRODUCT_ID)) continue;
            if (purchase.getPurchaseState() == Purchase.PurchaseState.PURCHASED) {
                owned = true;
                if (!purchase.isAcknowledged()) {
                    client.acknowledgePurchase(AcknowledgePurchaseParams.newBuilder()
                        .setPurchaseToken(purchase.getPurchaseToken()).build(), ignored -> { });
                }
            } else if (purchase.getPurchaseState() == Purchase.PurchaseState.PENDING) {
                pending = true;
            }
        }
        boolean wasUnlocked = RegionLock.isUnlocked(context);
        if (owned) RegionLock.setUnlocked(context, true);
        else if (authoritative) RegionLock.setUnlocked(context, false);
        String message = null;
        if (owned && !wasUnlocked) message = "已解鎖全部地區";
        else if (pending) message = "付款處理中，完成後會自動解鎖";
        listener.onBillingChanged(message);
    }
}
