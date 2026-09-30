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

    NAIJALINGO_API_KEY: str | None = None

    # Speaker Verification: Picovoice Eagle

    PICOVOICE_ACCESS_KEY: str | None = None
    SPEAKER_PROVIDER: str = "eagle"

    # Similarity score (0.0-1.0) at or above which a verification counts as
    # a match. Below this, the caller must fall back to PIN.
    SPEAKER_VERIFICATION_THRESHOLD: float = 0.8
    SPEAKER_MAX_AUDIO_BYTES: int = 10_000_000
    SPEAKER_MAX_DURATION_SECONDS: float = 30.0

    # ------------------------------------------------------------------ #
    # Domain constants                                                    #
    # ------------------------------------------------------------------ #
    # NGN is the only supported currency.  No LLM or tool may override   #
    # this. UI Pay remains the authoritative validator.
    DEFAULT_CURRENCY: str = "NGN"

    UIPAY_BASE_URL: str = "http://localhost:8001"
    UIPAY_SERVICE_TOKEN: str | None = None
    UIPAY_CLIENT_TYPE: str = "mock"
    UIPAY_TIMEOUT_SECONDS: float = 10.0

    LLM_PROVIDER: str = "mock"

    ASR_PROVIDER: str = "naijavox"
    ASR_MAX_AUDIO_BYTES: int = 10_000_000
    ASR_MAX_DURATION_SECONDS: float = 60.0
    ASR_NAIJAVOX_MODEL_ID: str = "Axiveri/NaijaVox-2.0"
    ASR_NAIJAVOX_DEVICE: str = "auto"
    ASR_FASTER_WHISPER_MODEL: str = "large-v3"
    ASR_FASTER_WHISPER_DEVICE: str = "auto"
    ASR_FASTER_WHISPER_COMPUTE_TYPE: str = "auto"

    OCR_PROVIDER: str = "paddleocr"

    # Maximum raw image payload size accepted before even decoding.
    # Default: 20 MB — generous enough for high-res screenshots; configurable.
    OCR_MAX_IMAGE_BYTES: int = 20_000_000

    # Transaction intelligence constants for bounded historical analysis.
    TRANSACTION_MAX_LOOKBACK_DAYS: int = 365
    TRANSACTION_SIGNIFICANT_CHANGE_PERCENT: float = 0.25
    TRANSACTION_MINIMUM_ABSOLUTE_CHANGE: float = 50000.00
    TRANSACTION_MINIMUM_OBSERVATION_PERIODS: int = 2

    # Maximum pixel count (width × height) to guard against decompression bombs.
    # Default: 50 MP (e.g. 10000×5000) — covers very large document scans.
    OCR_MAX_IMAGE_PIXELS: int = 50_000_000

    # PaddleOCR device: "auto" selects GPU if available, otherwise CPU.
    # "cpu" forces CPU.  "gpu" requires a CUDA GPU and fails clearly if absent.
    OCR_PADDLE_DEVICE: str = "auto"

    TTS_PROVIDER: str = "edge"
    TTS_DEFAULT_GENDER: str = "female"


settings = Settings()
