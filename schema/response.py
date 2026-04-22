"""
统一响应格式封装。
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式：{"code": 200, "msg": "", "data": ...}"""
    code: int
    msg: str
    data: T | None = None

    @classmethod
    def success(cls, data: T | None = None, msg: str = "success", code: int = 200) -> "ApiResponse[T]":
        """成功响应"""
        return cls(code=code, msg=msg, data=data)

    @classmethod
    def error(cls, msg: str, code: int = 500, data: T | None = None) -> "ApiResponse[T]":
        """错误响应"""
        return cls(code=code, msg=msg, data=data)


# ── 分页响应 ───────────────────────────────────────────────────────────────────


class PaginationResponse(BaseModel, Generic[T]):
    """分页响应封装：{items: [], total: 100, page: 1, page_size: 20, has_more: true}"""
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool

    @classmethod
    def from_list(
        cls,
        items: list[T],
        total: int,
        page: int = 1,
        page_size: int = 20,
    ) -> "PaginationResponse[T]":
        """从列表创建分页响应。"""
        start = (page - 1) * page_size
        end = start + page_size
        return cls(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
        )
