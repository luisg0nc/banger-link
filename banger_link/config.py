from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    telegram_token: str = Field(min_length=10)

    # NoDecode keeps pydantic-settings from JSON-parsing these env-var values;
    # the field validators below split them on our own delimiters instead.
    whitelisted_chat_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    ignored_domains: Annotated[list[str], NoDecode] = Field(default_factory=list)

    data_dir: Path = Path("./data")
    log_level: str = "INFO"
    health_port: int = 8080

    songlink_api_url: HttpUrl = HttpUrl("https://api.song.link/v1-alpha.1/links")

    digest_timezone: str = "UTC"
    digest_hour: int = 12  # post digests at this local hour

    @field_validator("whitelisted_chat_ids", mode="before")
    @classmethod
    def _parse_chat_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(p) for p in value.split(",") if p.strip()]
        return value

    @field_validator("ignored_domains", mode="before")
    @classmethod
    def _parse_domains(cls, value: object) -> object:
        if isinstance(value, str):
            return [p.strip() for p in value.split(";") if p.strip()]
        return value

    @property
    def db_path(self) -> Path:
        return self.data_dir / "banger.db"

    @property
    def digest_post_time(self) -> time:
        return time(hour=self.digest_hour, tzinfo=ZoneInfo(self.digest_timezone))


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
