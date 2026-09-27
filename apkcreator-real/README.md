# ApkCreator

A small Flask-based Android WebView project builder. It accepts a URL or HTML, generates an Android Studio project ZIP, and creates a debug APK when Gradle and the Android SDK are installed.

## Run

```bash
cd apkcreator-real
bash build.sh
```

Open http://localhost:5000. The JSON API is `POST /api/build`:

```json
{"name":"Example","package":"com.example.example","url":"https://example.com"}
```

The response includes a build ID and download filenames. Never expose this service publicly without authentication and resource limits; builds execute local tooling and consume disk/CPU.
