from datetime import datetime

from core import hash_password, BadRequestError
from sqlmodel.ext.asyncio.session import AsyncSession

from dao.user_dao import UserDAO
from model.user import User
from schema.user import UserCreate, UserUpdate


class UserService:
    def __init__(self) -> None:
        self.user_dao = UserDAO()

    async def create_user(self, session: AsyncSession, payload: UserCreate) -> User:
        existing_user = await self.user_dao.get_by_username(session, payload.username)
        if existing_user:
            raise BadRequestError(msg="用户名已存在")

        if payload.email:
            existing_email = await self.user_dao.get_by_email(session, payload.email)
            if existing_email:
                raise BadRequestError(msg="邮箱已被注册")

        payload_data = payload.model_dump()
        if not payload_data.get("created_by"):
            payload_data["created_by"] = "system"
        payload_data["updated_by"] = payload_data["created_by"]

        # 密码哈希（bcrypt）
        if payload_data.get("password"):
            payload_data["password"] = hash_password(payload_data["password"])

        user = User(**payload_data)
        return await self.user_dao.create(session, user)

    async def get_user(self, session: AsyncSession, user_id: int) -> User | None:
        return await self.user_dao.get_by_id(session, user_id)

    async def list_users(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
        return await self.user_dao.list(session, skip=skip, limit=limit)

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
        return await self.user_dao.search_users(
            session,
            keyword=keyword,
            created_by=created_by,
            start_at=start_at,
            end_at=end_at,
            skip=skip,
            limit=limit,
        )

    async def update_user(self, session: AsyncSession, user_id: int, payload: UserUpdate) -> User | None:
        update_data = payload.model_dump(exclude_unset=True)
        if update_data and "updated_by" not in update_data:
            update_data["updated_by"] = "system"

        if "username" in update_data:
            existing_user = await self.user_dao.get_by_username(session, update_data["username"])
            if existing_user and existing_user.id != user_id:
                raise BadRequestError(msg="用户名已存在")

        if "email" in update_data and update_data["email"]:
            existing_email = await self.user_dao.get_by_email(session, update_data["email"])
            if existing_email and existing_email.id != user_id:
                raise BadRequestError(msg="邮箱已被注册")

        return await self.user_dao.update(session, user_id, update_data)

    async def delete_user(self, session: AsyncSession, user_id: int) -> bool:
        return await self.user_dao.delete(session, user_id)

