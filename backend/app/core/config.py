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

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"

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
