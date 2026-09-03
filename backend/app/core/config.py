from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://astrohelp:astrohelp@localhost:5434/astrohelp"
    TEST_DATABASE_URL: str = (
        "postgresql+psycopg2://astrohelp:astrohelp@localhost:5434/astrohelp_test"
    )

    # Auth
    # Admin-login tokens only — signed and verified entirely by us (see
    # issue_admin_token/decode_admin_token). The astrologer side has no
    # signing at all: the main AstroLokal app hands off a plain user_id in
    # the webview URL, which we resolve directly against Astrologer.user_id
    # (see auth_service.resolve_astrologer_by_user_id) — confirmed 2026-08-14,
    # there is no shared secret or signature on that side.
    JWT_SECRET: str = "dev-only-change-me"
    ADMIN_TOKEN_EXPIRE_HOURS: int = 8

    # There is no self-service signup or per-user password reset — every admin
    # account is provisioned by an existing ADMIN-access admin (dashboard or
    # scripts/create_admin.py), and always gets the fixed password for the
    # access_level it was granted. Promoting/demoting an account resets its
    # password to the new tier's value.
    NORMAL_ACCESS_PASSWORD: str = "astroHelp@123"
    ADMIN_ACCESS_PASSWORD: str = "astroHelpAdmin@123"

    # This one email always gets ADMIN-access in with ADMIN_ACCESS_PASSWORD,
    # even if no Admin row exists yet (or it was deactivated) — solves the
    # bootstrap chicken-and-egg problem on a brand-new database (can't grant
    # yourself dashboard access without already being logged in to grant it)
    # without a permanent, un-auditable backdoor: see
    # auth_service._maybe_bootstrap_owner, which creates/reactivates a REAL
    # Admin row rather than a separate code path — deactivating it via the
    # dashboard later works normally from then on, same as any other admin.
    OWNER_EMAIL: str = "parth.a@getlokalapp.com"

    # Only used to build the Gemini billing label below ("production" or
    # "dev" — per the org's Vertex AI migration guide, 2026-08-18). Set this
    # per Devtron environment (production Secret -> "production", every
    # dev/staging Secret -> "dev").
    ENVIRONMENT: str = "dev"

    # Gemini, via Vertex AI (not a plain API key, as of 2026-08-18 — org
    # policy is off bare Gemini API keys, since usage on one lands in a
    # single untagged billing bucket nobody can attribute to a team/use
    # case). GEMINI_VERTEX_CREDENTIALS_JSON is a GCP service account's JSON,
    # same env-var convention (and parsing) as GOOGLE_SHEETS_CREDENTIALS_JSON.
    # No separate project setting — vertex_client reads project_id straight
    # off the credential itself, per the org's migration guide.
    GOOGLE_CLOUD_LOCATION: str = "global"
    GEMINI_VERTEX_CREDENTIALS_JSON: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    # The "{environment}_{feature}" billing label's feature half — see the
    # org's shared label-format guide. Coordinate with other teams before
    # changing this; it's the bucket cost gets attributed to.
    GEMINI_BILLING_FEATURE: str = "supply_help"

    # Mocked integrations
    MOCK_MODE: bool = True

    # Photo-beautify n8n workflow ("Astro Image Enhancement") — has its own
    # mock switch, same reasoning as SLACK_MOCK_MODE. The workflow's trigger
    # is a Form (not a plain webhook) and it has no "respond to caller" step
    # at all — its only output is a row appended to N8N_BEAUTIFY_LOG_SHEET_ID.
    # So going real means: POST multipart to the form URL, then poll that
    # sheet for a new row for this expert_id and read the "New Image" link
    # out of it — see app/integrations/n8n_client.py.
    N8N_MOCK_MODE: bool = True
    N8N_BEAUTIFY_FORM_URL: str = "https://n8n.getlokalapp.com/form/5702a402-783e-41d2-abef-934925b3ddb3"
    N8N_BEAUTIFY_LOG_SHEET_ID: str = "1YQEBHLRoQoL77PfUPxMZPjnzXaf18OTv0FGhsnkmRso"
    N8N_BEAUTIFY_LOG_TAB: str = "Images"
    N8N_BEAUTIFY_POLL_INTERVAL_SECONDS: int = 5
    N8N_BEAUTIFY_POLL_TIMEOUT_SECONDS: int = 90

    SLACK_WEBHOOK_URL: str = "https://hooks.slack.com/services/EXAMPLE/WEBHOOK/URL"
    SLACK_SUPPORT_CHANNEL: str = "#support-test"
    # Linked from every ticket-created Slack notification so a KAM/CS can
    # jump straight to it instead of hunting for the ticket in the dashboard.
    ADMIN_DASHBOARD_URL: str = "https://astro-supply-help-admin.astrolokal.com"
    # Slack has its own mock switch, independent of MOCK_MODE — a real Slack
    # webhook can go live on its own without payout/KYC/salary/etc. (which have
    # no real backend yet) needing to come along with it.
    SLACK_MOCK_MODE: bool = True
    # A ticket's photo/video gets pushed INTO Slack (not just linked back to
    # our own server) — durable regardless of our container's disk, and
    # syncs to a KAM/CS's Slack app in the background with no dashboard visit
    # needed. Needs a real Bot Token (files:write scope, bot invited to the
    # channel below) — the incoming webhook above can't upload files at all.
    # Gated by the same SLACK_MOCK_MODE, not a separate flag — it's the same
    # notification, just the attachment half of it.
    SLACK_BOT_TOKEN: str = ""
    # Slack channel ID (e.g. "C0123456789"), not a name — the file-upload
    # API needs an ID, unlike the incoming webhook above.
    SLACK_UPLOAD_CHANNEL_ID: str = ""

    # MoEngage — fired on every ticket status change (see
    # app/integrations/moengage_client.py) so their dashboard-side campaigns
    # can decide which transitions actually trigger a push notification to
    # the astrologer; this backend only ever emits the event, never a push
    # itself. Own mock switch, same reasoning as SLACK_MOCK_MODE. Real Data
    # API shape: POST {MOENGAGE_EVENT_API_URL} with HTTP basic auth
    # (MOENGAGE_APP_ID as username, MOENGAGE_API_KEY as password) — data
    # center subdomain (api-01/02/03/04) depends on the MoEngage account,
    # confirm the right one before flipping MOENGAGE_MOCK_MODE off.
    MOENGAGE_MOCK_MODE: bool = True
    MOENGAGE_EVENT_API_URL: str = "https://api-01.moengage.com/v1/event/{app_id}"
    MOENGAGE_APP_ID: str = ""
    MOENGAGE_API_KEY: str = ""

    # Zoho Desk — two-way ticket sync. Push: every cs_notified ticket gets
    # mirrored into Zoho on creation, kept in sync as its status changes
    # (see app/integrations/zoho_client.py, called from ticket_service.py).
    # Pull: a Zoho workflow-rule webhook posts to
    # /api/integrations/zoho/webhook (see app/api/routes/integrations/
    # zoho_webhook.py) on ticket status change there. Own mock switch, same
    # reasoning as SLACK_MOCK_MODE/MOENGAGE_MOCK_MODE. Unlike every other
    # integration here, Zoho auth is OAuth (client id/secret + refresh
    # token, not a static key) — zoho_client caches and refreshes the
    # short-lived access token itself.
    ZOHO_MOCK_MODE: bool = True
    ZOHO_ACCOUNTS_DOMAIN: str = "https://accounts.zoho.in"
    ZOHO_API_DOMAIN: str = "https://desk.zoho.in"
    ZOHO_CLIENT_ID: str = ""
    ZOHO_CLIENT_SECRET: str = ""
    ZOHO_REFRESH_TOKEN: str = ""
    ZOHO_ORG_ID: str = ""
    ZOHO_DEPARTMENT_ID: str = ""
    # Shared secret the inbound webhook checks for in the
    # X-Zoho-Webhook-Secret header — set this same value in the Zoho
    # workflow rule's webhook action. Not an OAuth credential; just a
    # bearer secret, same convention as everything else in this app.
    ZOHO_WEBHOOK_SECRET: str = ""

    # AI phone support, directly on Twilio Voice + ConversationRelay
    # (voice_client.py) — Twilio itself owns telephony/STT/TTS/
    # interruption-handling via
    # ConversationRelay, and streams transcribed caller speech to us over a
    # WebSocket (/api/voice/conversation-relay), to which we reply with
    # plain text. Own mock switch, same reasoning as SLACK_MOCK_MODE —
    # request-call logs a Call row and returns a fake twilio_call_sid
    # instead of actually dialing.
    VOICE_MOCK_MODE: bool = True
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    # The Twilio number calls are placed FROM (E.164, e.g. "+17372212163")
    # — must have Voice capability and a real balance behind it; a
    # trial-only number without funds can't complete real calls.
    TWILIO_PHONE_NUMBER: str = ""
    # Twilio signs both HTTP webhooks and the initial ConversationRelay
    # WebSocket handshake with the Auth Token. Set false only for local
    # TestClient tests; never disable this in a deployed environment.
    VOICE_VALIDATE_TWILIO_SIGNATURE: bool = True
    # Automatic ticket follow-up calls remain off until product approval;
    # administrators can still start a deliberate ticket call manually.
    VOICE_AUTO_CALL_ON_TICKET_CREATE: bool = False
    # Where Twilio fetches TwiML, posts call-status events, and opens the
    # ConversationRelay WebSocket — must be a publicly reachable https/wss
    # URL (Twilio is a third-party service, not on our network), so this is
    # never localhost outside of a tunnel (ngrok/etc.) during local dev.
    VOICE_PUBLIC_BASE_URL: str = "http://localhost:8000"

    # The phone agent's LLM — OpenRouter (https://openrouter.ai), not
    # Vertex/Gemini — see app/agent/openrouter_client.py. Deliberately
    # independent of the GEMINI_* settings above: text chat and the phone
    # agent are free to run on different model providers, since only the
    # tool-calling loop (orchestrator.py) and every tool in
    # tool_registry.py are actually shared between them.
    OPENROUTER_API_KEY: str = ""
    # Verified live against a real OpenRouter key on 2026-09-03 — several
    # Anthropic/Google model slugs 404'd ("No endpoints found") on that
    # account despite being valid OpenRouter model ids, most likely a
    # provider disabled in that account's OpenRouter settings rather than a
    # bad slug. Swap this for whichever model you actually want the phone
    # agent running on (see https://openrouter.ai/models), but if a swap
    # 404s, check the account's enabled providers before assuming the slug
    # is wrong.
    #
    # Switched from openai/gpt-4o-mini to this (2026-09-04) after live
    # latency complaints on a real call — measured on this account,
    # this model via Groq averaged ~0.44s per completion (incl. a tool
    # call) vs. ~1.32s for gpt-4o-mini, ~3x faster, and a phone turn
    # needing a tool is two completions back to back, so it compounds.
    # Confirmed tool-calling still works correctly via Groq before
    # switching, not just plain chat.
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct"
    # Comma-separated provider names, forces OpenRouter's routing rather
    # than letting it pick among whichever providers host this model slug
    # by its own policy — see app/agent/openrouter_client.py. Empty means
    # "let OpenRouter choose". Leave this in sync with whichever provider
    # OPENROUTER_MODEL above was actually benchmarked/verified against.
    OPENROUTER_PROVIDER_ORDER: str = "groq"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    # Uploads — astrologer-shared photos/videos (screenshots, profile photos).
    # "local" (default): written to disk, served back out at
    # {PUBLIC_BASE_URL}/uploads/<file> — fine for a single instance, lost on
    # redeploy/restart/scale-out (see app/core/uploads.py). "s3": written to
    # S3_BUCKET_NAME (must be public-read, or served via signed URLs later)
    # — survives redeploys and multiple replicas. Swapping this is a one-flag
    # change; nothing outside app/integrations/object_storage.py and the
    # upload route needs to know which backend is active.
    UPLOADS_BACKEND: str = "local"
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    # Key prefix within the bucket (e.g. "supply-issues/") — whoever
    # provisions the bucket may scope IAM/lifecycle policy to a specific
    # prefix rather than the bucket root. Include the trailing slash.
    S3_KEY_PREFIX: str = "uploads/"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Email has its own mock switch, same reasoning as SLACK_MOCK_MODE — no
    # real email provider is wired up yet, so this stays true until one is.
    EMAIL_MOCK_MODE: bool = True
    ADMIN_APP_BASE_URL: str = "http://localhost:5174"

    # Google Sheets sync — read-only service account, path never committed
    # (see backend/.gitignore). See app/services/sheets_sync_service.py.
    # 2026-08-14: switched to the real KYC and Payout sheets (previous two
    # sheets fully retired — see docs/chatbot-approach.md §8a).
    GOOGLE_SHEETS_CREDENTIALS_PATH: str = "credentials/google-sheets-service-account.json"
    # Deployments that only hand us env vars, not files (e.g. a k8s Secret),
    # set this instead — the credential file's own JSON content, raw or
    # base64. Takes priority over GOOGLE_SHEETS_CREDENTIALS_PATH when set.
    GOOGLE_SHEETS_CREDENTIALS_JSON: str = ""
    KYC_SPREADSHEET_ID: str = ""
    PAYOUT_SPREADSHEET_ID: str = ""
    # The payout-amount tab rotates every cycle (e.g. "July 31 - 1") — the
    # roster tab ("Expert ID") is stable with no such rotation. Update this
    # when ops adds a new cycle tab; no code change needed.
    PAYOUT_CYCLE_TAB: str = "July 31 - 1"

    # Expert priority ranking — a saved analytics query's results as CSV
    # (Redash-style "results.csv?api_key=..." URL, secret baked in). Full
    # URL, not split into pieces, since it's used verbatim as one GET.
    # Replaces the old (frozen since 2026-08-14) queue-performance sheet's
    # priority column — see app/services/sheets_sync_service.py.
    PRIORITY_QUERY_CSV_URL: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
