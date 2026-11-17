from functools import lru_cache

from app.core.errors import ApiError
from app.core.passwords import PasswordService
from app.db.owners import OwnerRepository
from app.schemas.auth import LoginRequest, OwnerProfile
from app.services.sessions import SessionCredentials, SessionService


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    # Unknown accounts still perform the same expensive password verification.
    return PasswordService().hash("unused dummy account passphrase")


class AuthService:
    def __init__(
        self, owners: OwnerRepository, sessions: SessionService, passwords: PasswordService
    ) -> None:
        self.owners = owners
        self.sessions = sessions
        self.passwords = passwords

    def login(self, data: LoginRequest, raw_token: str) -> tuple[OwnerProfile, SessionCredentials]:
        fallback_hash = dummy_password_hash()
        owner = self.owners.find_by_email(data.email)
        verified = self.passwords.verify(
            owner.password_hash if owner else fallback_hash, data.password.get_secret_value()
        )
        if not verified or owner is None:
            raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
        profile = OwnerProfile.model_validate(owner)
        credentials = self.sessions.rotate(raw_token, owner.id)
        return profile, credentials

    def profile(self, owner_id: str) -> OwnerProfile:
        owner = self.owners.find_by_id(owner_id)
        if owner is None:
            raise ApiError(401, "authentication_required", "A valid owner session is required.")
        return OwnerProfile.model_validate(owner)
