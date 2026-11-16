from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.session_cookies import SessionCookies
from app.api.session_dependencies import (
    get_session_service,
    require_auth_origin,
    require_csrf_session,
    require_owner_mutation,
    require_owner_session,
)
from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.core.passwords import PasswordService
from app.db.models import BrowserSession
from app.db.owners import OwnerRepository
from app.db.session import RateLimitSessionLocal, get_db
from app.schemas.auth import LoginRequest, OwnerProfile
from app.schemas.errors import ErrorResponse
from app.schemas.sessions import CsrfResponse
from app.services.auth import AuthService
from app.services.rate_limits import LoginRateLimiter
from app.services.sessions import SessionService

router = APIRouter(prefix="/auth", tags=["owner authentication"])


def get_auth_service(
    db: Annotated[Session, Depends(get_db)],
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> AuthService:
    return AuthService(OwnerRepository(db), sessions, PasswordService())


def get_login_limiter(config: Annotated[Settings, Depends(get_settings)]) -> LoginRateLimiter:
    return LoginRateLimiter(RateLimitSessionLocal, config)


@router.post(
    "/login",
    response_model=OwnerProfile,
    dependencies=[Depends(require_csrf_session)],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 422, 429, 503)},
)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    limiter: Annotated[LoginRateLimiter, Depends(get_login_limiter)],
) -> OwnerProfile:
    limiter.enforce_login(request.client.host if request.client else "unknown", data.email)
    try:
        profile, credentials = service.login(data, request.cookies[config.session_cookie_name])
        expires = credentials.record.expires_at
        max_age = service.sessions.remaining_seconds(credentials.record)
        db.commit()
    except (ApiError, SQLAlchemyError):
        db.rollback()
        raise
    SessionCookies(config).set(response, credentials.raw_token, expires, max_age)
    response.headers["Cache-Control"] = "no-store"
    return profile


@router.get(
    "/me",
    response_model=OwnerProfile,
    responses={code: {"model": ErrorResponse} for code in (401, 403, 503)},
)
def me(
    response: Response,
    owner_session: Annotated[BrowserSession, Depends(require_owner_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> OwnerProfile:
    profile = service.profile(owner_session.owner_id)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Cookie, Origin"
    return profile


@router.post(
    "/logout",
    status_code=204,
    responses={code: {"model": ErrorResponse} for code in (401, 403, 503)},
)
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[Settings, Depends(get_settings)],
    sessions: Annotated[SessionService, Depends(get_session_service)],
    owner_session: Annotated[BrowserSession, Depends(require_owner_mutation)],
) -> Response:
    try:
        sessions.revoke(request.cookies.get(config.session_cookie_name))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    SessionCookies(config).clear(response)
    return response


@router.get(
    "/csrf",
    response_model=CsrfResponse,
    dependencies=[Depends(require_auth_origin)],
    responses={403: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Start or reuse a session and retrieve its CSRF token",
)
def get_csrf(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[SessionService, Depends(get_session_service)],
    config: Annotated[Settings, Depends(get_settings)],
) -> CsrfResponse:
    credentials = service.bootstrap(request.cookies.get(config.session_cookie_name))
    body = CsrfResponse(csrf_token=credentials.record.csrf_token)
    max_age = service.remaining_seconds(credentials.record)
    expires = credentials.record.expires_at
    # Persist successfully before sending any credential to the browser.
    db.commit()
    SessionCookies(config).set(response, credentials.raw_token, expires, max_age)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Vary"] = "Cookie, Origin"
    return body
