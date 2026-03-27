"""
统一响应格式封装。
"""
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

