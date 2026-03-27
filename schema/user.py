from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel


class UserCreate(SQLModel):
    username: str
    password: str
    email: Optional[str] = None
    created_by: Optional[str] = None


class UserUpdate(SQLModel):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    updated_by: Optional[str] = None


class UserRead(SQLModel):
    id: int
    username: str
    email: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

