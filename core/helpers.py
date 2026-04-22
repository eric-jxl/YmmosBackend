"""
通用工具函数：IP 提取、时间格式化等。
"""
from datetime import datetime, timezone
from typing import Any


def get_client_ip(request: Any) -> str:
    """从 FastAPI request 中提取客户端 IP。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def now_utc() -> datetime:
    """获取当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def utc_to_datetime(dt: datetime) -> datetime:
    """将带时区的 datetime 转换为无时区（便于比较）。"""
    return dt.replace(tzinfo=None)
