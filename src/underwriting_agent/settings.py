from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    knowledge_agent_base_url: str = "http://127.0.0.1:8001"
    knowledge_agent_timeout_seconds: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
