plugins {
    id("com.android.application")
}

android {
    namespace = "com.codex.amigurumiweather"
    compileSdk = 36

    signingConfigs {
        getByName("debug") {
            storeFile = file("../work/manual-build/debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    defaultConfig {
        applicationId = "com.codex.amigurumiweather"
        minSdk = 26
        targetSdk = 36
        versionCode = 433
        versionName = "4.33"
    }

    flavorDimensions += "device"
    productFlavors {
        create("universal") {
            dimension = "device"
        }
        create("galaxyZFold5") {
            dimension = "device"
        }
        create("admin") {
            dimension = "device"
            applicationIdSuffix = ".admin"
            versionNameSuffix = "-admin"
        }
    }
}
