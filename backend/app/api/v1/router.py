from fastapi import APIRouter

from app.api.v1.endpoints import (
    agentes,
    auth,
    finance,
    health,
    informes,
    merge,
    operaciones,
    procesos,
    proveedores,
    reporteador,
    reports,
    sharepoint,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(reports.router)
api_router.include_router(reporteador.router)
api_router.include_router(proveedores.router)
api_router.include_router(merge.router)
api_router.include_router(operaciones.router)
api_router.include_router(sharepoint.router)
api_router.include_router(agentes.router)
api_router.include_router(informes.router)
api_router.include_router(procesos.router)
api_router.include_router(finance.router)
