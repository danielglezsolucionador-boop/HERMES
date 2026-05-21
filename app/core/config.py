from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # App
    APP_NAME: str = 'hermes'
    APP_ENV: Literal['development', 'staging', 'production'] = 'development'
    APP_VERSION: str = '0.1.0'
    DEBUG: bool = False

    # Server
    HOST: str = '0.0.0.0'
    PORT: int = 8000

    # Database
    DATABASE_URL: str = 'postgresql+asyncpg://user:pass@localhost/hermes'

    # AI providers
    AI_PROVIDER: str = 'openrouter'
    CLAUDE_API_KEY: str = ''
    CLAUDE_REAL_REQUESTS_ENABLED: bool = False
    OPENROUTER_API_KEY: str = ''

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ''
    TELEGRAM_CHAT_ID: int = 0

    # Logging
    LOG_LEVEL: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'
    LOG_FORMAT: Literal['text', 'json'] = 'text'

    # Runtime loop
    RUNTIME_LOOP_INTERVAL_SECONDS: float = 5.0
    RUNTIME_LOOP_MIN_INTERVAL_SECONDS: float = 0.5
    RUNTIME_LOOP_DEGRADED_ERROR_THRESHOLD: int = 3
    RUNTIME_LOOP_MAX_CONSECUTIVE_ERRORS: int = 5
    RUNTIME_LOOP_SAFETY_EVENT_LIMIT: int = 20

    @field_validator('PORT')
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError('PORT must be between 1024 and 65535')
        return v


settings = Settings()
