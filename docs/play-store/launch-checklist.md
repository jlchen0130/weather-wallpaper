# Google Play 上架清單

## 版本與商品

- 上架用的是 `play` flavor：`gradle bundlePlayRelease`，輸出 `app/build/outputs/bundle/playRelease/app-play-release.aab`。
- 套件名稱 `com.codex.amigurumiweather`。第一次上傳之後就**永遠不能改**，要換名稱必須在第一次上傳前決定。
- 內購商品（一次性、不可消耗）：ID 是 `unlock_all_regions`，要在 Play Console →「營利」→「產品」→「應用程式內產品」建立，ID 要一字不差。
- 免費版：鎖定在第一次成功定位的縣市（只限台灣 22 縣市）。還沒定位成功前，顯示高雄的桌布，但不會鎖定。
- 已購買：可以跟著 GPS 走，或指定 22 縣市其中一個。重新安裝、換手機時，只要是同一個 Google 帳號，打開 App 就會自動恢復。退款後下次開 App 會恢復鎖定。

## 上架金鑰（使用者自己做）

1. 產生上傳金鑰（密碼自己設定，不要給任何人）：

   ```powershell
   & "C:\Program Files\Android\Android Studio1\jbr\bin\keytool.exe" -genkeypair -v -keystore "$HOME\keys\amigurumi-upload.jks" -alias upload -keyalg RSA -keysize 4096 -validity 10000
   ```

2. 在專案根目錄建立 `keystore.properties`（已列在 .gitignore，不會進 Git）：

   ```
   storeFile=C:/Users/JL/keys/amigurumi-upload.jks
   storePassword=你設定的密碼
   keyAlias=upload
   keyPassword=你設定的密碼
   ```

3. 備份 `.jks` 檔和密碼。遺失的話要向 Google 申請重設上傳金鑰。
4. 上架時使用「Play 應用程式簽署」，讓 Google 保管真正的發布金鑰。

## Play Console 要填的項目

- **應用程式存取權**：所有功能都不需要登入。
- **廣告**：無廣告。
- **內容分級**：問卷照實填（無暴力、無使用者互動內容），預期是「適合所有人」。
- **目標對象**：13 歲以上（避免落入兒童政策）。
- **隱私權政策網址**：`docs/play-store/privacy-policy.md` 要放在公開網址上（例如 GitHub Pages 或 Worker 的 /privacy 頁面）。
- **資料安全性**：
  - 收集「大概位置」和「精確位置」，用途是「應用程式功能」。資料會傳輸（加密），不分享給第三方，非必要（可以拒絕權限）。
  - 購買紀錄由 Google Play 處理，不必申報。
  - 不收集其他資料類型。
- **權限聲明**：只用前景定位，不需要背景定位聲明。

## 商店資訊（草稿）

- 名稱：Amigurumi Weather 天氣桌布
- 簡短說明（80 字內）：依照你所在縣市的天氣和時段，自動換上羊毛氈風格的台灣城市桌布。
- 完整說明：
  - 晴天、雨天、颱風、日出到深夜，桌布會跟著天氣和時間自動變化。
  - 台灣 22 縣市各有在地地標的羊毛氈微縮場景，節日還有限定版本。
  - 免費版固定在你第一次定位的縣市；一次購買「解鎖全部地區」，就能隨時切換 22 縣市。
  - 沒有廣告、不需要註冊帳號。
- 圖片素材：App 圖示 512×512、主題圖片 1024×500、手機截圖至少 2 張（建議 4～8 張直式）。

## 測試與上線流程（個人開發者帳號）

1. 建立「內部測試」，上傳 AAB，用自己的帳號安裝測試內購（把自己加進「授權測試人員」，購買不會真的扣款）。
2. 建立「封閉測試」，邀請至少 12 位測試者，**連續 14 天**都保持加入。
3. 期滿後在 Play Console 申請正式版存取權，送審正式版。
