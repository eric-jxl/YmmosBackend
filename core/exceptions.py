"""
统一异常类型定义。
替代混用的 ValueError / AuthFlowError，提供清晰的错误分类。
"""
from __future__ import annotations


class APIException(Exception):
    """API 异常基类。"""

    def __init__(self, msg: str = "请求失败", code: int = 400, data: dict | None = None) -> None:
        super().__init__(msg)
        self.msg = msg
        self.code = code
        self.data = data


class AuthenticationError(APIException):
    """认证失败：401"""

    def __init__(self, msg: str = "未授权访问", data: dict | None = None) -> None:
        super().__init__(msg=msg, code=401, data=data)


class PermissionDenied(APIException):
    """权限不足：403"""

    def __init__(self, msg: str = "权限不足", data: dict | None = None) -> None:
        super().__init__(msg=msg, code=403, data=data)


class ResourceNotFoundError(APIException):
    """资源不存在：404"""

    def __init__(self, msg: str = "资源不存在", data: dict | None = None) -> None:
        super().__init__(msg=msg, code=404, data=data)


class BadRequestError(APIException):
    """请求错误：400"""

    def __init__(self, msg: str = "请求参数错误", data: dict | None = None) -> None:
        super().__init__(msg=msg, code=400, data=data)


class RateLimitExceeded(APIException):
    """请求频率超限：429"""

    def __init__(self, msg: str = "请求过于频繁，请稍后重试", wait_seconds: int = 60, data: dict | None = None) -> None:
        data = data or {}
        data["wait_seconds"] = wait_seconds
        super().__init__(msg=msg, code=429, data=data)


class PreconditionRequired(APIException):
    """ precondition 不满足（如 TOTP 未绑定）：428"""

    def __init__(self, msg: str = "需要先完成前置操作", data: dict | None = None) -> None:
        super().__init__(msg=msg, code=428, data=data)


class ServerError(APIException):
    """服务器内部错误：500"""

    def __init__(self, msg: str = "服务器内部错误", data: dict | None = None) -> None:
        super().__init__(msg=msg, code=500, data=data)


# ── 兼容性别名 ────────────────────────────────────────────────────────────────

AuthFlowError = PreconditionRequired
