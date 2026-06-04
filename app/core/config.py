from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "omi-command-hub"
    app_env: str = "development"
    app_base_url: str = "http://localhost"

    database_url: str = "postgresql+psycopg://omi_user:change_me@postgres:5432/omi_command_hub"
    redis_url: str = "redis://redis:6379/0"

    omi_webhook_secret: str = ""
    omi_signing_secret: str = ""
    omi_app_id: str = ""
    omi_app_secret: str = ""
    omi_api_key: str = ""
    omi_notify: bool = True
    omi_api_base: str = "https://api.omi.me"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    default_tz: str = "America/Chicago"

    notion_token: str = ""
    notion_database_id: str = ""
    notion_prop_name: str = "Name"
    notion_prop_due: str = "Due"
    notion_prop_priority: str = "Priority"
    notion_prop_tags: str = "Tags"
    notion_prop_people: str = "People"
    notion_prop_location: str = "Location"
    notion_prop_notes: str = "Notes"
    notion_prop_fingerprint: str = "Fingerprint"

    google_chat_webhook_url: str = ""

    home_assistant_base_url: str = ""
    home_assistant_token: str = ""

    log_level: str = "INFO"
    legacy_omi_routes: bool = False

    admin_username: str = "admin"
    admin_password: str = ""

    cors_allowed_origins: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_allowed_origins:
            return []
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
