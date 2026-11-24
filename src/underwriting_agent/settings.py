from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DATABASE_PATH = DATA_DIR / "underwriting_agent.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    knowledge_agent_base_url: str = "http://127.0.0.1:8001"
    knowledge_agent_timeout_seconds: float = 20.0

    portfolio_analyst_base_url: str = "http://127.0.0.1:8003"
    portfolio_analyst_timeout_seconds: float = 30.0
    portfolio_analyst_underwriting_years: list[int] = [2024, 2025]

    submission_extractor_base_url: str = "http://127.0.0.1:8000"
    submission_extractor_timeout_seconds: float = 30.0

    database_url: str = f"sqlite:///{DEFAULT_DATABASE_PATH}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
