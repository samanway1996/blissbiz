from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.business_slugs import router as business_slugs_router
from app.api.errors import register_exception_handlers
from app.api.health import router as health_router
from app.api.media import router as media_router
from app.api.registrations import router as registrations_router
from app.api.upload_limits import UploadLimitMiddleware

app = FastAPI(
    title="BlissBiz API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.add_middleware(UploadLimitMiddleware)
app.include_router(health_router, prefix="/api")
app.include_router(business_slugs_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(registrations_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(media_router)
register_exception_handlers(app)
