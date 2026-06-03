from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8080"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_path: str = os.getenv("DATABASE_PATH", "data/devin_automation.db")
    github_webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "dev-only-secret")
    github_label: str = os.getenv("GITHUB_TRIGGER_LABEL", "devin-remediate")
    github_issue_comment_token: str | None = os.getenv("GITHUB_TOKEN")
    devin_api_base: str = os.getenv("DEVIN_API_BASE", "https://api.devin.ai")
    devin_api_key: str | None = os.getenv("DEVIN_API_KEY")
    devin_org_id: str | None = os.getenv("DEVIN_ORG_ID")
    devin_repo_url: str | None = os.getenv("DEVIN_REPO_URL")
    devin_mode: str = os.getenv("DEVIN_MODE", "normal")
    devin_poll_interval_seconds: int = int(os.getenv("DEVIN_POLL_INTERVAL_SECONDS", "20"))
    devin_max_acu_limit: int = int(os.getenv("DEVIN_MAX_ACU_LIMIT", "20"))
    mock_devin: bool = _as_bool(os.getenv("MOCK_DEVIN"), default=True)


settings = Settings()
