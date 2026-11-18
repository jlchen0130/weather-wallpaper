import java.util.Properties

plugins {
    id("com.android.application")
}

// Upload-key settings for Google Play live outside Git in keystore.properties:
// storeFile=..., storePassword=..., keyAlias=..., keyPassword=...
val releaseKeyProps = Properties().apply {
    val file = rootProject.file("keystore.properties")
    if (file.exists()) file.inputStream().use { load(it) }
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
        if (releaseKeyProps.getProperty("storeFile") != null) {
            create("release") {
                storeFile = rootProject.file(releaseKeyProps.getProperty("storeFile"))
                storePassword = releaseKeyProps.getProperty("storePassword")
                keyAlias = releaseKeyProps.getProperty("keyAlias")
                keyPassword = releaseKeyProps.getProperty("keyPassword")
            }
        }
    }

    buildFeatures {
        buildConfig = true
    }

    defaultConfig {
        applicationId = "com.codex.amigurumiweather"
        minSdk = 26
        targetSdk = 36
        versionCode = 438
        versionName = "4.38"
        buildConfigField("boolean", "REGION_LOCK", "false")
    }

    buildTypes {
        getByName("release") {
            signingConfig = signingConfigs.findByName("release")
        }
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
        // Google Play build: free tier is locked to the first GPS county/city,
        // the one-time in-app product unlock_all_regions opens every region.
        create("play") {
            dimension = "device"
            buildConfigField("boolean", "REGION_LOCK", "true")
        }
    }
}

dependencies {
    implementation("com.android.billingclient:billing:8.0.0")
}
