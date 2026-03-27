from __future__ import annotations

from fnmatch import fnmatch
from typing import Iterable, Sequence

import jwt
from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from schema.response import ApiResponse


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Global JWT guard with path-pattern based public endpoint exceptions."""

    def __init__(
        self,
        app,
        *,
        secret: str,
        algorithm: str,
        public_path_patterns: Sequence[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._secret = secret
        self._algorithm = algorithm
        self._public_patterns = tuple(public_path_patterns or ())

    def _is_public_path(self, path: str) -> bool:
        return any(fnmatch(path, pattern) for pattern in self._public_patterns)

    @staticmethod
    def _extract_bearer_token(request: Request) -> str | None:
        raw = request.headers.get("Authorization", "")
        if not raw.startswith("Bearer "):
            return None
        token = raw[7:].strip()
        return token or None

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or self._is_public_path(request.url.path):
            return await call_next(request)

        token = self._extract_bearer_token(request)
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ApiResponse.error(
                    msg="缺少访问令牌，请先登录",
                    code=status.HTTP_401_UNAUTHORIZED,
                ).model_dump(),
            )

        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ApiResponse.error(
                    msg="访问令牌已过期，请重新登录",
                    code=status.HTTP_401_UNAUTHORIZED,
                ).model_dump(),
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ApiResponse.error(
                    msg="访问令牌无效，请重新登录",
                    code=status.HTTP_401_UNAUTHORIZED,
                ).model_dump(),
            )

        request.state.auth_user = {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "jti": payload.get("jti"),
        }
        return await call_next(request)


def default_public_path_patterns() -> Iterable[str]:
    """Default anonymous paths; everything else is protected by middleware."""
    return (
        "/",
        "/health",
        "/login",
        "/docs",
        "/docs/*",
        "/redoc",
        "/redoc/*",
        "/openapi.json",
        "/static/*",
        "/favicon.ico",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/totp/login",
        "/api/v1/auth/totp/setup/*",
        "/api/v1/auth/totp/confirm/*",
        "/api/v1/auth/github",
        "/api/v1/auth/github/callback",
    )

