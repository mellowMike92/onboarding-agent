import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./onboarding_agent.db"
    )
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    cors_origins: tuple[str, ...] = tuple(
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    )

    @property
    def agent_mode(self) -> str:
        """'live' when an Anthropic key is configured, else deterministic 'mock'."""
        return "live" if self.anthropic_api_key else "mock"


settings = Settings()
