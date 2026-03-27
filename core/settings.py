from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_name: str = "SQLModel API"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = True
    app_workers: int = 4

    # Database
    database_url: str = "sqlite+aiosqlite:///sqlmodel.db"
    db_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    db_pool_timeout: int = 30          # 等待连接的超时秒数（MySQL/PG 有效）

    @property
    def db_type(self) -> str:
        """从 database_url 推断数据库类型：sqlite | mysql | postgresql。"""
        url = self.database_url.lower()
        if "mysql" in url or "mariadb" in url:
            return "mysql"
        if "postgresql" in url or "postgres" in url:
            return "postgresql"
        return "sqlite"

    # JWT
    jwt_secret: str = "change-me-use-a-strong-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h

    # GitHub OAuth2
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""

    # TOTP rate-limit
    totp_max_failures: int = 3       # 最大连续失败次数
    totp_lockout_seconds: int = 60   # 锁定时长（秒）

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
