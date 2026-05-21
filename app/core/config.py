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
    TASK_DISCOVERY_LIMIT: int = 10
    TASK_DISCOVERY_MAX_PAYLOAD_BYTES: int = 4096
    TASK_DISCOVERY_QUERY_TIMEOUT_SECONDS: float = 3.0
    TASK_CLAIMING_ENABLED: bool = False
    TASK_CLAIMING_MAX_CONCURRENT_CLAIMS: int = 1
    TASK_CLAIMING_MAX_ATTEMPTS_PER_CYCLE: int = 1
    TASK_CLAIMING_MAX_TASK_ATTEMPTS: int = 3
    TASK_CLAIMING_MIN_INTERVAL_SECONDS: float = 60.0
    TASK_CLAIMING_STALE_AFTER_SECONDS: int = 900
    TASK_CLAIMING_MAX_STALE_CLAIMS: int = 5
    TASK_PICKUP_SAFETY_ENABLED: bool = True
    TASK_PICKUP_SAFETY_MAX_RETRIES: int = 2
    TASK_PICKUP_SAFETY_RETRY_WINDOW_SECONDS: int = 300
    TASK_PICKUP_SAFETY_MAX_ORPHANED_CLAIMS: int = 0
    TASK_PICKUP_SAFETY_MAX_INVALID_CLAIMS: int = 0
    TASK_PICKUP_SAFETY_MAX_FOREIGN_RUNTIME_CLAIMS: int = 1000
    TASK_EXECUTION_ENABLED: bool = False
    TASK_EXECUTION_MAX_CONCURRENT_EXECUTIONS: int = 1
    TASK_EXECUTION_MAX_DURATION_SECONDS: int = 300
    TASK_EXECUTION_MAX_RUNTIME_LOAD: float = 1.0
    TASK_EXECUTION_MAX_MEMORY_MB: int = 512
    TASK_EXECUTION_SAFETY_ENABLED: bool = True
    TASK_EXECUTION_SAFETY_MAX_RETRIES: int = 2
    PROVIDER_BRIDGE_ENABLED: bool = False
    PROVIDER_BRIDGE_MAX_REQUESTS_PER_MINUTE: int = 5
    PROVIDER_BRIDGE_MAX_REQUEST_BYTES: int = 8192
    PROVIDER_BRIDGE_TIMEOUT_SECONDS: float = 25.0
    PROVIDER_BRIDGE_MAX_CONCURRENT_CALLS: int = 1
    PROVIDER_BRIDGE_MAX_RESPONSE_BYTES: int = 32768
    PROVIDER_BRIDGE_MAX_TOKENS: int = 2048
    RESPONSE_INGESTION_ENABLED: bool = True
    RESPONSE_INGESTION_MAX_RESPONSE_BYTES: int = 32768
    RESPONSE_INGESTION_MAX_DURATION_MS: int = 1000
    RESPONSE_INGESTION_MAX_CONCURRENT_INGESTIONS: int = 1
    RESPONSE_INGESTION_MAX_RUNTIME_LOAD: float = 1.0
    RESPONSE_VALIDATION_ENABLED: bool = True
    RESPONSE_VALIDATION_MAX_PAYLOAD_BYTES: int = 32768
    RESPONSE_VALIDATION_MAX_DURATION_MS: int = 500
    RESPONSE_VALIDATION_MAX_CONCURRENT_VALIDATIONS: int = 1
    RESPONSE_VALIDATION_MAX_RUNTIME_LOAD: float = 1.0
    RESPONSE_SAFETY_ENABLED: bool = True
    RESPONSE_SAFETY_MAX_PAYLOAD_BYTES: int = 32768
    RESPONSE_SAFETY_MAX_DURATION_MS: int = 250
    RESPONSE_SAFETY_MAX_CONCURRENT_CHECKS: int = 1
    RESPONSE_SAFETY_MAX_RUNTIME_LOAD: float = 1.0
    RESPONSE_SAFETY_MAX_VALIDATION_RETRIES: int = 1
    TIMEOUT_CONTROL_ENABLED: bool = True
    TIMEOUT_CONTROL_MAX_CONCURRENT_CHECKS: int = 1
    TIMEOUT_CONTROL_MAX_TRACKING_DURATION_SECONDS: int = 600
    TIMEOUT_CONTROL_MAX_RUNTIME_LOAD: float = 1.0
    TIMEOUT_CONTROL_MAX_CHECK_DURATION_MS: int = 250
    RETRY_CONTROL_ENABLED: bool = True
    RETRY_CONTROL_MAX_ATTEMPTS: int = 3
    RETRY_CONTROL_MAX_CONCURRENT_RETRIES: int = 1
    RETRY_CONTROL_MAX_DURATION_MS: int = 1000
    RETRY_CONTROL_MAX_RUNTIME_LOAD: float = 1.0
    RETRY_CONTROL_MAX_OVERHEAD_MS: int = 250
    RUNNER_ID: str = "hermes-runner"
    RUNTIME_ID: str = "hermes-runtime"

    @field_validator('PORT')
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError('PORT must be between 1024 and 65535')
        return v


settings = Settings()
