from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, jobs, logs, stream, summary, topology

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(summary.router)
api_router.include_router(logs.router)
api_router.include_router(topology.router)
api_router.include_router(jobs.router)
api_router.include_router(stream.router)

