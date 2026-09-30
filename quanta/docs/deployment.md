# Quanta Microservice — Operational Deployment & Configuration Guide

## 1. Environment Configuration (`.env`)

Copy `.env.example` to `.env` and configure operational parameters:

```ini
# Application Setup
APP_NAME=Quanta
ENVIRONMENT=production
LOG_LEVEL=INFO

# Provider Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
GROQ_API_KEY=your_groq_api_key
PICOVOICE_ACCESS_KEY=your_picovoice_key

# Host UI Pay Backend Settings
UIPAY_BASE_URL=http://uipay-backend:8001
UIPAY_SERVICE_TOKEN=your_internal_service_token
UIPAY_TIMEOUT_SECONDS=10.0
UIPAY_MAX_RETRIES=2

# Provider Selection
LLM_PROVIDER=mock
ASR_PROVIDER=naijavox
OCR_PROVIDER=paddleocr
TTS_PROVIDER=edge
SPEAKER_PROVIDER=eagle

# Security & Constraints
DEFAULT_CURRENCY=NGN
SPEAKER_VERIFICATION_THRESHOLD=0.8
ASR_MAX_AUDIO_BYTES=10000000
OCR_MAX_IMAGE_BYTES=20000000
```

---

## 2. Health & Readiness Endpoints

Quanta provides operational probes for load balancers and deployment orchestrators:

- **Liveness Probe**: `GET /health` returns `{ "status": "ok", "app": "Quanta" }`
- **Readiness Probe**: `GET /api/v1/health` checks sub-component provider configuration and system dependencies.

---

## 3. Production Logging & Data Privacy

Quanta uses structured JSON logging with built-in secret redaction:
- Sensitive parameters (`pin`, `password`, `token`, `api_key`, `bvn`, `audio`, `voice_profile`) are automatically replaced with `[REDACTED]`.
- Binary audio and biometric speaker profile payloads are sanitized as `[BYTES payload len=N]`.

---

## 4. Startup Command

Run Quanta using `uvicorn` / `gunicorn` in production:

```bash
# Production server startup
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```
