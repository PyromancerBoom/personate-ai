from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_provider: Literal["gemini", "openai"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    playwright_headless: bool = False
    max_journey_steps: int = 12
    runs_dir: Path = Path("../runs")
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ]
    viewport_width: int = 1280
    viewport_height: int = 900


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
