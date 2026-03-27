"""
安全审计日志 DAO。
核心能力：记录安全事件、查询近期失败次数（用于速率限制）。
"""
from datetime import UTC, datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from dao.base import BaseDAO
from model.auth_log import AuthLog


class AuthLogDAO(BaseDAO[AuthLog]):

    def __init__(self) -> None:
        super().__init__(AuthLog)

    async def count_recent_failures(
        self,
        session: AsyncSession,
        username: str,
        event: str,
        window_seconds: int = 60,
    ) -> int:
        """统计 window_seconds 内指定用户的指定事件次数。"""
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=window_seconds)
        statement = (
            select(AuthLog)
            .where(AuthLog.username == username)
            .where(AuthLog.event == event)
            .where(AuthLog.created_at >= since)
        )
        result = await session.exec(statement)
        return len(result.all())

    async def get_last_failure_time(
        self,
        session: AsyncSession,
        username: str,
        event: str,
    ) -> datetime | None:
        """获取最近一次指定事件的发生时间（用于计算剩余锁定时长）。"""
        statement = (
            select(AuthLog)
            .where(AuthLog.username == username)
            .where(AuthLog.event == event)
            .order_by(AuthLog.created_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        result = await session.exec(statement)
        log = result.first()
        return log.created_at if log else None

