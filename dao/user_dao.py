from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from dao.base import BaseDAO
from model.user import User


class UserDAO(BaseDAO[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_username(self, session: AsyncSession, username: str) -> User | None:
        return await self.get_by_field(session, "username", username)

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        return await self.get_by_field(session, "email", email)

    async def search_users(
        self,
        session: AsyncSession,
        *,
        keyword: str | None = None,
        created_by: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        like_filters = {"username": keyword} if keyword else None
        filters = {"created_by": created_by} if created_by else None
        range_filters = {"created_at": (start_at, end_at)} if (start_at or end_at) else None

        return await self.query_list(
            session,
            filters=filters,
            like_filters=like_filters,
            range_filters=range_filters,
            order_by=[("created_at", "desc")],
            skip=skip,
            limit=limit,
        )

