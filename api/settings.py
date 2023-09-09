from os import environ
from pathlib import Path
from typing import Dict, Literal

from pydantic import field_validator
from pydantic_core.core_schema import FieldValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

environ.setdefault("ENV_FILE", "dev.env")

BASE_DIR: Path = Path(__file__).parent

ENV_DIR: Path = BASE_DIR / "environment"
ENV_FILE: Path = ENV_DIR / environ["ENV_FILE"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE)

    # Base
    ROOT_PATH: Path = BASE_DIR

    API_NAME: str
    API_VERSION: str

    META: dict | None = None

    @field_validator("META")
    def meta(cls, value, values: FieldValidationInfo, **kwargs):  # noqa
        return {
            "version": values.data.get("API_VERSION"),
        }

    MEDIA_DIR: Path = "media"

    @field_validator("MEDIA_DIR", mode="before")
    def media_dir(cls, value: str, values: FieldValidationInfo, **kwargs) -> Path:  # noqa
        return values.data.get("ROOT_PATH") / value

    DEBUG: bool = False

    # Media
    MAX_MEDIA_SIZE: int | float = 6 * 1024 * 1024  # Bytes. Default 6 MB

    # Database
    DB_DRIVER: str

    DB_NAME: str

    DB_HOST: str | None = None
    DB_PORT: int | None = None

    DB_USER: str | None = None
    DB_PASS: str | None = None

    ECHO_SQL: bool = DEBUG

    FORCE_INIT: bool = False

    DB_URL: URL | None = None

    @field_validator("DB_URL")
    def db_url(
        cls,
        value: URL | None,
        values: FieldValidationInfo,
        **kwargs,
    ) -> URL:
        return URL.create(
            values.data.get("DB_DRIVER"),
            values.data.get("DB_USER"),
            values.data.get("DB_PASS"),
            values.data.get("DB_HOST"),
            values.data.get("DB_PORT"),
            values.data.get("DB_NAME"),
        )

    # Logging
    SENTRY: str | None = None

    LOGLEVEL: Literal["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    LOG_FORMAT: str

    LOG_DATETIME_FORMAT: str

    LOGS_DIR: Path = "logs"

    @field_validator("LOGS_DIR", mode="before")
    def logs_dir(cls, value: str, values: FieldValidationInfo, **kwargs) -> Path:  # noqa
        return values.data.get("ROOT_PATH") / "logging_data" / value

    LOGFILE_NAME: Path = "api.log"

    @field_validator("LOGFILE_NAME", mode="before")
    def logfile_name(
        cls,
        value: str,
        values: FieldValidationInfo,
        **kwargs,
    ) -> Path:
        return values.data.get("LOGS_DIR") / value

    LOGFILE_SIZE: int
    LOGFILE_COUNT: int

    LOGGING: Dict | None = None

    @field_validator("LOGGING")
    def logging(
        cls,
        value: None,
        values: FieldValidationInfo,
        **kwargs,
    ) -> Dict:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "base": {
                    "format": values.data.get("LOG_FORMAT"),
                    "datefmt": values.data.get("LOG_DATETIME_FORMAT"),
                },
                "colour": {
                    "()": "logging_data.formatters.ColourFormatter",
                    "fmt": values.data.get("LOG_FORMAT"),
                    "datefmt": values.data.get("LOG_DATETIME_FORMAT"),
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": values.data.get("LOGLEVEL"),
                    "formatter": "colour",
                },
                "logfile": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": values.data.get("LOGLEVEL"),
                    "filename": values.data.get("LOGFILE_NAME"),
                    "maxBytes": values.data.get("LOGFILE_SIZE"),
                    "backupCount": values.data.get("LOGFILE_COUNT"),
                    "formatter": "base",
                },
            },
            "root": {
                "level": values.data.get("LOGLEVEL"),
                "handlers": ["console", "logfile"],
            },
        }


settings = Settings()
