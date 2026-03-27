from typing import Optional

from sqlmodel import Field

from model.base import AuditModel


class User(AuditModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    username: str = Field(unique=True, index=True)
    password: Optional[str] = Field(default=None, nullable=True)  # bcrypt hash，GitHub 用户可为空
    email: Optional[str] = Field(default=None, unique=True)
    is_active: bool = Field(default=True)

    # TOTP
    totp_secret: Optional[str] = Field(default=None)        # base32 secret
    totp_enabled: bool = Field(default=False)

    # GitHub OAuth2
    github_id: Optional[str] = Field(default=None, unique=True, index=True)
