from fastapi import FastAPI, Header, HTTPException

from app.core.config import settings
from app.core.constants import Operations
from app.core.context import RequestContext

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }

@app.get("/context-test")
async def context_test(
    x_user_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
):
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail="Missing user context",
        )

    if not x_session_id:
        raise HTTPException(
            status_code=401,
            detail="Missing session context",
        )

    context = RequestContext.create(
        user_id=x_user_id,
        session_id=x_session_id,
        operation=Operations.VOICE,
        metadata={
            "channel": "test",
        },
    )

    return {
        "request_id": str(context.request_id),
        "user_id": context.user_id,
        "session_id": context.session_id,
        "operation": context.operation,
        "locale": context.locale,
    }