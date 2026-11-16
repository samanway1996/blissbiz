from fastapi import FastAPI
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.business_slugs import router as business_slugs_router
from app.api.errors import register_exception_handlers
from app.api.health import router as health_router
from app.api.media import router as media_router
from app.api.registrations import router as registrations_router
from app.api.storefront import router as storefront_router
from app.api.upload_limits import UploadLimitMiddleware
from app.core.config import Settings, get_settings, settings


def create_app(config: Settings = settings) -> FastAPI:
    application = FastAPI(
        title="BlissBiz API",
        version="0.1.0",
        docs_url="/api/docs" if config.app_env == "development" else None,
        openapi_url="/api/openapi.json" if config.app_env == "development" else None,
        redoc_url=None,
    )
    application.dependency_overrides[get_settings] = lambda: config
    application.add_middleware(UploadLimitMiddleware)
    application.add_middleware(ProxyHeadersMiddleware, trusted_hosts=config.trusted_proxy_ips)
    for router in (health_router,):
        application.include_router(router, prefix="/api")
    for router in (
        business_slugs_router,
        auth_router,
        registrations_router,
        admin_router,
        storefront_router,
    ):
        application.include_router(router, prefix="/api/v1")
    application.include_router(media_router)
    register_exception_handlers(application)
    return application


app = create_app()
