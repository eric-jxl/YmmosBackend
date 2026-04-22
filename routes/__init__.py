
from fastapi import APIRouter

from routes.user_route import router as user_router
from routes.auth_route import router as auth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(user_router)
api_router.include_router(auth_router)

__all__ = ["api_router"]
