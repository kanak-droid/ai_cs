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
    JWT_SECRET: str = "dev-only-change-me"
    ASTROLOGER_TOKEN_ALGORITHM: str = "HS256"
    ADMIN_TOKEN_EXPIRE_HOURS: int = 8

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Mocked integrations
    MOCK_MODE: bool = True
    N8N_BEAUTIFY_WEBHOOK_URL: str = "https://n8n.example.com/webhook/photo-beautify"
    SLACK_WEBHOOK_URL: str = "https://hooks.slack.com/services/EXAMPLE/WEBHOOK/URL"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
