"""Configuração lida exclusivamente de variáveis de ambiente (nunca grave segredos no código)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _list_int(value: str | None) -> list[int]:
    out: list[int] = []
    for part in (value or "").replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.append(int(part))
    return out


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", "")))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./serviceconnect.db"))
    db_schema: str = field(default_factory=lambda: os.getenv("DB_SCHEMA", "serviceconnect"))
    # Render define RENDER_EXTERNAL_URL automaticamente
    webhook_base_url: str = field(default_factory=lambda: (os.getenv("WEBHOOK_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/"))
    webhook_secret: str = field(default_factory=lambda: os.getenv("WEBHOOK_SECRET", ""))
    admin_username: str = field(default_factory=lambda: os.getenv("ADMIN_USERNAME", "admin"))
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    admin_telegram_ids: list[int] = field(default_factory=lambda: _list_int(os.getenv("ADMIN_TELEGRAM_IDS")))
    session_secret: str = field(default_factory=lambda: os.getenv("SESSION_SECRET", ""))
    support_contact: str = field(default_factory=lambda: os.getenv("SUPPORT_CONTACT", ""))
    company_name: str = field(default_factory=lambda: os.getenv("COMPANY_NAME", "ServiceConnect"))
    # anti-spam
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")))
    max_requests_per_day: int = field(default_factory=lambda: int(os.getenv("MAX_REQUESTS_PER_DAY", "10")))
    max_proposals_per_day: int = field(default_factory=lambda: int(os.getenv("MAX_PROPOSALS_PER_DAY", "40")))
    max_notifications_per_request: int = field(default_factory=lambda: int(os.getenv("MAX_NOTIFICATIONS_PER_REQUEST", "50")))

    @property
    def webhook_path(self) -> str:
        return "/telegram/webhook"

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_base_url}{self.webhook_path}" if self.webhook_base_url else ""


settings = Settings()
