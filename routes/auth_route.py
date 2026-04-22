"""
认证路由。
  POST /auth/totp/login             - TOTP 登录
  POST /auth/totp/setup/{user_id}   - 为用户生成 TOTP secret + QR URI
  GET  /auth/github                 - 跳转 GitHub 授权页
  GET  /auth/github/callback        - GitHub 回调，换取 JWT
"""
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from core import (
    get_client_ip,
    generate_state_token,
    BadRequestError,
    AuthenticationError,
    PreconditionRequired,
)
from service.auth_service import AuthService
from schema.auth import (
    CombinedLoginRequest,
    TOTPLoginRequest,
    TOTPSetupResponse,
    TokenResponse,
    RegisterRequest,
    RegisterResponse,
    TOTPConfirmRequest,
)
from schema.response import ApiResponse

router = APIRouter(prefix="/auth", tags=["auth"])
_auth_service = AuthService()


# ── 注册 ──────────────────────────────────────────────────────────────────────
# ── 注册 ──────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED,
             summary="注册新账号（自动生成 TOTP 绑定信息）")
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    注册新账号并返回 TOTP otpauth URI，供前端生成二维码引导用户扫码绑定。
    """
    try:
        result = await _auth_service.register(
            session, payload,
            ip=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
        )
        return ApiResponse.success(data=result, msg="注册成功")
    except BadRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/totp/confirm/{user_id}",
             summary="首次绑定 TOTP：验证 App 生成的验证码，成功后直接登录")
async def confirm_totp(
    user_id: int,
    payload: TOTPConfirmRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await _auth_service.confirm_totp(
            session, user_id, payload.code,
            ip=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
        )
        return ApiResponse.success(data=result, msg="绑定成功")
    except BadRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── 密码 + 动态口令 联合登录 ──────────────────────────────────────────────────

@router.post("/login", summary="用户名 + 密码（+ 动态口令）登录")
async def login(
    payload: CombinedLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    主登录端点。\n
    - 未绑定 TOTP：需先扫码绑定\n
    - 已绑定 TOTP：必须同时提交 6 位动态口令
    """
    try:
        result = await _auth_service.combined_login(
            session, payload,
            ip=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
        )
        return ApiResponse.success(data=result, msg="登录成功")
    except PreconditionRequired as exc:
        raise HTTPException(status_code=exc.code, detail=exc.data)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


# ── TOTP ──────────────────────────────────────────────────────────────────────

@router.post("/totp/login", summary="TOTP 动态令牌登录")
async def totp_login(
    payload: TOTPLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    使用用户名 + 6 位 TOTP 动态令牌登录。
    - 失败 3 次后锁定 60 秒
    - 所有事件写入安全审计日志
    """
    try:
        result = await _auth_service.totp_login(
            session,
            payload,
            ip=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
        )
        return ApiResponse.success(data=result, msg="登录成功")
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post(
    "/totp/setup/{user_id}",
    summary="初始化 TOTP（生成 secret + otpauth URI）",
)
async def setup_totp(
    user_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    为指定用户生成 TOTP 密钥并返回 otpauth:// URI。
    客户端用 URI 生成二维码，用户用 Authenticator App 扫码绑定。
    """
    try:
        result = await _auth_service.setup_totp(session, user_id)
        return ApiResponse.success(data=result, msg="TOTP 初始化成功")
    except BadRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── GitHub OAuth2 ─────────────────────────────────────────────────────────────

@router.get("/github", summary="跳转至 GitHub OAuth 授权页")
async def github_login():
    """生成 state 后跳转至 GitHub OAuth 授权页面。"""
    state = generate_state_token()
    try:
        redirect_url = _auth_service.get_github_auth_url(state)
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except ValueError as exc:
        params = urlencode({"oauth": "error", "message": str(exc)})
        return RedirectResponse(url=f"/login#{params}", status_code=status.HTTP_302_FOUND)


@router.get("/github/callback", summary="GitHub OAuth 回调")
async def github_callback(
    code: str,
    request: Request,
    format: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """
    GitHub 回调端点：用 code 换取用户信息，自动创建或关联账号。
    - 浏览器请求：重定向回 /login#oauth=...
    - API 请求：附加 ?format=json 返回 TokenResponse JSON
    """
    wants_json = format == "json" or "application/json" in request.headers.get("accept", "")

    try:
        token = await _auth_service.github_callback(
            session,
            code=code,
            ip=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
        )

        if wants_json:
            return token

        params = urlencode(
            {
                "oauth": "success",
                "access_token": token.access_token,
                "token_type": token.token_type,
                "expires_in": token.expires_in,
            }
        )
        return RedirectResponse(url=f"/login#{params}", status_code=status.HTTP_302_FOUND)
    except ValueError as exc:
        if wants_json:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        params = urlencode({"oauth": "error", "message": str(exc)})
        return RedirectResponse(url=f"/login#{params}", status_code=status.HTTP_302_FOUND)
    except Exception as exc:
        detail = f"GitHub OAuth 服务异常：{exc}"
        if wants_json:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
        params = urlencode({"oauth": "error", "message": detail})
        return RedirectResponse(url=f"/login#{params}", status_code=status.HTTP_302_FOUND)
