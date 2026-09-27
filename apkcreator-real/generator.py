"""Generate a minimal, reproducible Android WebView project.

The generator always produces a source ZIP. If Gradle and the Android SDK are
available, it also produces a debug APK; otherwise the source ZIP is still a
valid deliverable and the API reports the reason an APK was skipped.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile
import zipfile

class BuildError(Exception):
    pass


def _safe(value, fallback):
    value = re.sub(r"[^A-Za-z0-9 ._-]", "", value).strip()
    return value or fallback


def _package(value):
    value = value.lower().strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", value):
        raise ValueError("package must look like com.example.app")
    return value


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_project(config, output):
    name = _safe(config.get("name"), "Web App")
    package = _package(config.get("package", "com.example.webapp"))
    code = int(config.get("version_code", 1))
    if code < 1:
        raise ValueError("version_code must be positive")
    version = _safe(config.get("version_name"), "1.0.0")
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "project"
        pkgpath = Path(*package.split("."))
        _write(root / "settings.gradle", "pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\nrootProject.name='ApkCreatorApp'\ninclude ':app'\n")
        _write(root / "build.gradle", "plugins { id 'com.android.application' version '8.5.2' apply false }\n")
        _write(root / "gradle.properties", "android.useAndroidX=true\norg.gradle.jvmargs=-Xmx2g\n")
        _write(root / "app/build.gradle", f"""plugins {{ id 'com.android.application' }}

android {{ namespace '{package}'; compileSdk 35
    defaultConfig {{ applicationId '{package}'; minSdk 23; targetSdk 35; versionCode {code}; versionName '{version}' }}
}}

""")
        manifest = f'''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:theme="@style/AppTheme" android:label="{name}" android:usesCleartextTraffic="{'true' if config.get('allow_http') else 'false'}">
        <activity android:name=".MainActivity" android:exported="true"><intent-filter>
            <action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/>
        </intent-filter></activity>
    </application>
</manifest>'''
        _write(root / "app/src/main/AndroidManifest.xml", manifest)
        _write(root / "app/src/main/res/values/styles.xml", '<resources><style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar"><item name="android:fontFamily">sans</item><item name="android:colorAccent">#3f51b5</item></style></resources>')
        activity = f'''package {package};
import android.app.Activity; import android.os.Bundle; import android.webkit.WebSettings; import android.webkit.WebView;
public class MainActivity extends Activity {{ public void onCreate(Bundle b) {{ super.onCreate(b); WebView w=new WebView(this); WebSettings s=w.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); w.setWebViewClient(new android.webkit.WebViewClient()); setContentView(w); {'w.loadUrl("'+config['url']+'");' if config.get('url') else 'w.loadUrl("file:///android_asset/index.html");'} }} }}'''
        _write(root / f"app/src/main/java/{pkgpath}/MainActivity.java", activity)
        html = config.get("html") or '<!doctype html><html><body><h1>Web App</h1></body></html>'
        _write(root / "app/src/main/assets/index.html", html)
        zip_path = output / "android-project.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in root.rglob("*"):
                if file.is_file(): archive.write(file, file.relative_to(root))
        result = {"source": zip_path.name, "apk": None, "message": "Android source project created"}
        gradle = shutil.which("gradle")
        if gradle:
            try:
                subprocess.run([gradle, "assembleDebug", "--no-daemon"], cwd=root, check=True, timeout=300, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                apk = root / "app/build/outputs/apk/debug/app-debug.apk"
                if apk.exists(): shutil.copy2(apk, output / "app-debug.apk"); result.update(apk="app-debug.apk", message="APK created")
            except (subprocess.SubprocessError, OSError):
                result["message"] = "Source project created; APK compilation was unavailable"
        else:
            result["message"] = "Source project created; install Gradle and Android SDK to compile the APK"
        return result
