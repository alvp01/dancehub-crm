from fastapi import APIRouter

from app.routers import auth, health, operator

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(operator.router)
