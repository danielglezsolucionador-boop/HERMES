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

    # Logging
    LOG_LEVEL: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'
    LOG_FORMAT: Literal['text', 'json'] = 'text'

    @field_validator('PORT')
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError('PORT must be between 1024 and 65535')
        return v


settings = Settings()