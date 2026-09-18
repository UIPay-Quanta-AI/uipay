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
    CLAUDE_MODEL: str = "claude-sonnet-5"
    CLAUDE_MAX_TOKENS: int = 2048
    CLAUDE_TIMEOUT_SECONDS: float = 60.0
    CLAUDE_MAX_RETRIES: int = 2
    CLAUDE_DISABLE_PARALLEL_TOOL_USE: bool = True

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_MAX_TOKENS: int = 2048
    GROQ_TIMEOUT_SECONDS: float = 60.0
    GROQ_MAX_RETRIES: int = 2
    GROQ_DISABLE_PARALLEL_TOOL_USE: bool = True

    # ------------------------------------------------------------------ #
    # Domain constants                                                    #
    # ------------------------------------------------------------------ #
    # NGN is the only supported currency.  No LLM or tool may override   #
    # this. UI Pay remains the authoritative validator.
    DEFAULT_CURRENCY: str = "NGN"

    UIPAY_BASE_URL: str = "http://localhost:8001"
    UIPAY_SERVICE_TOKEN: str | None = None

    LLM_PROVIDER: str = "mock"

    ASR_PROVIDER: str = "naijavox"
    OCR_PROVIDER: str = "paddleocr"
    TTS_PROVIDER: str = "edge"


settings = Settings()
