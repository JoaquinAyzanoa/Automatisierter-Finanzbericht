from fastapi import APIRouter

from app.api.v1.endpoints import auth, finance, health, reports

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(reports.router)
api_router.include_router(finance.router)
