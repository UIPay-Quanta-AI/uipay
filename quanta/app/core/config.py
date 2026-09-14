from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Quanta"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    ANTHROPIC_API_KEY: str | None = None
    UIPAY_BASE_URL: str = "http://localhost:8001"
    UIPAY_SERVICE_TOKEN: str | None = None

    LLM_PROVIDER: str = "claude"
    ASR_PROVIDER: str = "naijavox"
    OCR_PROVIDER: str = "paddleocr"
    TTS_PROVIDER: str = "edge"


settings = Settings()
