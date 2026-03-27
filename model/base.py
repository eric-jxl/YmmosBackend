from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AuditModel(SQLModel):
    """基础审计字段，供业务模型复用。"""

    created_by: Optional[str] = Field(default=None, max_length=64)
    updated_by: Optional[str] = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

