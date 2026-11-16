from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.schemas.registrations import Email


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Email
    password: SecretStr = Field(min_length=1, max_length=128)


class OwnerProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    full_name: str
    email: str
