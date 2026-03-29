"""
数据库会话管理。
支持 SQLite（aiosqlite）、MySQL（asyncmy）、PostgreSQL（asyncpg）。
引擎参数、连接池大小和迁移策略根据数据库类型自动分支。
"""
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from core import get_settings

settings = get_settings()

# ── Engine 构建 ────────────────────────────────────────────────────────────────

_engine_kwargs: dict = {
    "echo": settings.db_echo,
    "pool_pre_ping": True,
    "pool_recycle": settings.db_pool_recycle,
}

if settings.db_type == "sqlite":
    # SQLite：不需要多进程同线程检查，也不设 pool_size / max_overflow / pool_timeout
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # MySQL / PostgreSQL：完整连接池配置
    _engine_kwargs.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout,
        }
    )

engine = create_async_engine(settings.database_url, **_engine_kwargs)

session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ── 幂等迁移定义 ────────────────────────────────────────────────────────────────
# (table, column, SQL type definition)
_MIGRATIONS: list[tuple[str, str, str]] = [
    ("users", "created_by", "VARCHAR(64)"),
    ("users", "updated_by", "VARCHAR(64)"),
    ("users", "created_at", "DATETIME"),
    ("users", "updated_at", "DATETIME"),
    ("users", "is_active", "BOOLEAN NOT NULL DEFAULT 1"),
    ("users", "totp_secret", "VARCHAR(64)"),
    ("users", "totp_enabled", "BOOLEAN NOT NULL DEFAULT 0"),
    ("users", "github_id", "VARCHAR(64)"),
]


# ── SQLite 迁移 ────────────────────────────────────────────────────────────────
async def _migrate_sqlite(conn) -> None:  # type: ignore[type-arg]
    for table, column, definition in _MIGRATIONS:
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        existing = {row[1] for row in result.fetchall()}
        if column not in existing:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))

    await conn.execute(
        text(
            "UPDATE users "
            "SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP), "
            "    updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)"
        )
    )
    # 部分唯一索引（SQLite 支持 WHERE 子句，NULL 不参与唯一约束）
    await conn.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_github_id "
            "ON users (github_id) WHERE github_id IS NOT NULL"
        )
    )


# ── MySQL 迁移 ─────────────────────────────────────────────────────────────────
async def _migrate_mysql(conn) -> None:  # type: ignore[type-arg]
    for table, column, definition in _MIGRATIONS:
        result = await conn.execute(
            text(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                f"WHERE TABLE_NAME='{table}' AND COLUMN_NAME='{column}' "
                "AND TABLE_SCHEMA=DATABASE()"
            )
        )
        if not result.fetchone():
            await conn.execute(
                text(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
            )

    # MySQL 不支持带 WHERE 的部分索引；MySQL 的 UNIQUE 索引对多个 NULL 行视为互不冲突
    result = await conn.execute(
        text(
            "SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS "
            "WHERE TABLE_NAME='users' AND INDEX_NAME='ix_users_github_id' "
            "AND TABLE_SCHEMA=DATABASE()"
        )
    )
    if not result.fetchone():
        await conn.execute(
            text("CREATE UNIQUE INDEX ix_users_github_id ON users (github_id)")
        )


# ── PostgreSQL 迁移 ────────────────────────────────────────────────────────────
async def _migrate_postgresql(conn) -> None:  # type: ignore[type-arg]
    for table, column, definition in _MIGRATIONS:
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                f"WHERE table_name='{table}' AND column_name='{column}'"
            )
        )
        if not result.fetchone():
            # PostgreSQL 9.6+ 支持 ADD COLUMN IF NOT EXISTS
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
            )

    # PostgreSQL 支持带 WHERE 的部分唯一索引（NULL 不参与唯一约束）
    await conn.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_github_id "
            "ON users (github_id) WHERE github_id IS NOT NULL"
        )
    )


# ── 公共 API ───────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """初始化数据库表结构并执行幂等补列迁移。"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        if settings.db_type == "sqlite":
            await _migrate_sqlite(conn)
        elif settings.db_type == "mysql":
            await _migrate_mysql(conn)
        elif settings.db_type == "postgresql":
            await _migrate_postgresql(conn)


async def close_db() -> None:
    """关闭并释放数据库连接池。"""
    try:
        await engine.dispose()
    except Exception:
        # 忽略错误，避免阻塞关闭流程
        pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：提供异步数据库会话，用完自动关闭。"""
    async with session_factory() as session:
        yield session
