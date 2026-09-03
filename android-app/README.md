# AstroHelp Android

Native Kotlin + Jetpack Compose client for the astrologer-facing AstroHelp API
(the same backend the `chat-app` webview talks to). Astrologers can chat with the
AI support bot and track their tickets.

This is a **self-contained Gradle project** that lives inside the `ai_cs`
monorepo but is not wired into the Node/Python build. Open it on its own.

## Open & run in Android Studio

1. **File → Open** and select this `android-app/` folder (not the repo root —
   the repo root has no Gradle build, so Android Studio won't sync it).
2. Let Gradle sync. A `app` run configuration appears automatically.
3. Pick an emulator (or device) and hit **Run**.

CLI equivalent:

```bash
./gradlew :app:assembleDebug        # build the debug APK
./gradlew :app:installDebug         # install on a running emulator/device
```

## Talking to the backend

The base URL is a `BuildConfig` field in `app/build.gradle.kts`:

```kotlin
buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000\"")
```

- `10.0.2.2` is the Android **emulator's** alias for the host machine's
  `localhost` — where the backend runs via `uvicorn` in local dev (see the repo
  README). On a physical device, change this to your machine's LAN IP.
- Cleartext HTTP is enabled (`usesCleartextTraffic="true"`) for local dev.

Start the backend first (from the repo root):

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
```

## Auth & the wrapper entry point

The astrologer side has **no signed token** — the main AstroLokal app hands off a
plain `user_id`, which the backend resolves against `Astrologer.user_id`
(see `backend/app/services/auth_service.py`). It's sent as
`Authorization: Bearer <user_id>` on every request.

`MainActivity` is a **wrapper entry point** designed to be launched directly by
the existing AstroLokal app, which already knows who the astrologer is. When a
`user_id` is handed off, there is **no login screen** — it authenticates and
drops straight into the chat.

From the host app (once this is a dependency / merged in):

```kotlin
// convenience helper:
MainActivity.start(context, astrologerUserId = 12345L)

// or an explicit intent:
val intent = Intent(context, MainActivity::class.java)
intent.putExtra("user_id", "12345")          // String or numeric extra both work
intent.putExtra("base_url", "https://...")   // optional backend override
context.startActivity(intent)
```

Fallback order when **no** `user_id` is handed off (standalone / dev runs):
saved session (`SharedPreferences`, see `data/SessionStore.kt`) → login screen.
For manual testing you can simulate the handoff over adb:

```bash
adb shell am start -n com.astrolokal.astrohelp/.MainActivity --es user_id 1
```

Use a `user_id` that exists in your local DB's `astrologers` table.

### Merging into the host app later

Right now this is a standalone `com.android.application` so it runs on its own.
To embed it, convert `:app` to a `com.android.library` module (drop
`applicationId` / the `LAUNCHER` intent-filter, apply `com.android.library`),
add it as a dependency of the host app, and launch `MainActivity` via the
handoff above. The UI, networking, and state layers need no changes.

## Structure

```
app/src/main/java/com/astrolokal/astrohelp/
  MainActivity.kt              Compose entry point
  data/
    Models.kt                  @Serializable mirrors of the backend schemas
    ApiClient.kt               HttpURLConnection + kotlinx.serialization
    SessionStore.kt            persists the logged-in user_id
  ui/
    AppViewModel.kt            auth / chat / tickets state (StateFlow)
    AstroHelpApp.kt            root scaffold + bottom nav (Chat / Tickets)
    LoginScreen.kt
    ChatScreen.kt
    TicketsScreen.kt
    TicketDetailScreen.kt      status history + resolution rating
    StatusStyle.kt             TicketStatus labels + colors
    theme/                     Material3 theme
```

## Versions

Gradle 9.4.1 · AGP 9.2.1 · Kotlin 2.2.10 · Compose BOM 2026.02.01 · minSdk 24 ·
targetSdk 36 · compileSdk 37.1 (aligned with the other Android projects on this
machine so dependencies are already cached).
