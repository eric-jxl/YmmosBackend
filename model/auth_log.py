"""
安全审计日志模型。
不继承 AuditModel 以保持轻量（只需 created_at，无需 updated_at / created_by 等）。
使用朴素 UTC 时间以保证 SQLite 字符串比较的正确性。
"""
from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AuthEvent:
    """安全事件类型常量。"""

    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    TOTP_FAILED = "TOTP_FAILED"
    TOTP_LOCKED = "TOTP_LOCKED"
    TOTP_SETUP = "TOTP_SETUP"
    GITHUB_LOGIN = "GITHUB_LOGIN"
    TOKEN_REFRESH = "TOKEN_REFRESH"


class AuthLog(SQLModel, table=True):
    __tablename__ = "auth_logs"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    user_id: Optional[int] = Field(default=None, index=True)
    username: str = Field(max_length=128, index=True)
    event: str = Field(max_length=32)        # AuthEvent 常量
    method: str = Field(max_length=16)       # TOTP | GITHUB
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=256)
    detail: Optional[str] = Field(default=None, max_length=512)
    # SQLite 不支持时区存储，使用朴素 UTC 保证字符串范围比较正确
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        index=True,
    )

