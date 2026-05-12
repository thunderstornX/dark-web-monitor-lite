"""Process settings loaded from environment / .env.

Every external dependency is optional. The matcher engine (the
measured component) runs entirely offline; Tor connectivity,
webhook delivery, and any LLM augmentation are all opt-in and
gracefully degraded."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process configuration. Pulled from env, .env, or constructor args."""

    # Optional Tor SOCKS5 proxy.
    tor_socks_url: str | None = "socks5://127.0.0.1:9050"

    # Optional webhook destinations.
    slack_webhook_url:   str | None = None
    discord_webhook_url: str | None = None
    generic_webhook_url: str | None = None

    # rapidfuzz threshold (0..100).
    fuzzy_threshold: int = 85

    # Network budgets.
    fetch_timeout_s: float = 30.0
    fetch_retries:   int   = 3
    webhook_timeout_s: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


def load_settings(**overrides) -> Settings:
    """Construct Settings, accepting test-time overrides as kwargs."""
    return Settings(**overrides)
