plugins {
    id("com.android.application")
}

android {
    namespace = "com.codex.amigurumiweather"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.codex.amigurumiweather"
        minSdk = 26
        targetSdk = 36
        versionCode = 303
        versionName = "3.3"
    }

    flavorDimensions += "device"
    productFlavors {
        create("universal") {
            dimension = "device"
        }
        create("galaxyZFold5") {
            dimension = "device"
        }
    }
}
