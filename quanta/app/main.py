from fastapi import FastAPI, Header, HTTPException

from app.api.v1.router import v1_router
from app.core.config import settings
from app.core.constants import Operations
from app.core.context import RequestContext
from app.schemas.response import QuantaResponse

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

app.include_router(v1_router, prefix="/api")


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


@app.get("/response-test", response_model=QuantaResponse)
async def response_test(
    x_user_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
):
    if not x_user_id or not x_session_id:
        raise HTTPException(status_code=401, detail="Missing trusted context")

    context = RequestContext.create(
        user_id=x_user_id,
        session_id=x_session_id,
        operation=Operations.VOICE,
    )

    # Demonstrate a confirmation-style response
    return QuantaResponse.confirmation_required(
        request_id=context.request_id,
        speech_text="Confirm transfer of five thousand naira to Amaka Okafor.",
        data={
            "amount": 5000,
            "currency": "NGN",
            "recipient_name": "Amaka Okafor",
        },
    )
