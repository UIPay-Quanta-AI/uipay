"""
API v1 Router aggregating all Quanta microservice endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.budget import router as budget_router
from app.api.v1.endpoints.goals import router as goals_router
from app.api.v1.endpoints.interact import router as interact_router
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.transactions import router as transactions_router
from app.api.v1.endpoints.voice import router as voice_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(interact_router)
v1_router.include_router(voice_router)
v1_router.include_router(profile_router)
v1_router.include_router(goals_router)
v1_router.include_router(budget_router)
v1_router.include_router(transactions_router)
