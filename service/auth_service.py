"""
认证业务服务。
涵盖：
  - TOTP 登录（含速率限制：3 次失败锁 60 秒）
  - TOTP 初始化（为用户生成 secret + otpauth URI）
  - GitHub OAuth2 授权码换取 JWT
  - JWT 签发
所有安全事件均写入 auth_logs 并通过 security_logger 输出到独立日志文件。
"""
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
import jwt
import pyotp
from loguru import logger
from passlib.context import CryptContext
from sqlmodel.ext.asyncio.session import AsyncSession

from core.settings import get_settings
from core.logger import security_logger
from dao.auth_log_dao import AuthLogDAO
from dao.user_dao import UserDAO
from model.auth_log import AuthEvent, AuthLog
from model.user import User
from schema.auth import (
    TOTPLoginRequest, TOTPSetupResponse, TokenResponse,
    PasswordLoginRequest, CombinedLoginRequest,
    RegisterRequest, RegisterResponse,
)

settings = get_settings()
_pwd_ctx = CryptContext(schemes=["scrypt"], deprecated="auto")


class AuthFlowError(ValueError):
    def __init__(self, status_code: int, detail: dict[str, object]) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class AuthService:

    def __init__(self) -> None:
        self._user_dao = UserDAO()
        self._log_dao = AuthLogDAO()

    # ── JWT ──────────────────────────────────────────────────────────────────

    @classmethod
    def create_token(cls, user_id: int, username: str) -> TokenResponse:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": str(user_id),
            "username": username,
            "exp": expire,
            "iat": datetime.now(UTC),
            "jti": secrets.token_hex(16),  # 防重放唯一标识
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_expire_minutes * 60,
        )

    # ── TOTP 初始化 ───────────────────────────────────────────────────────────

    async def setup_totp(
            self,
            session: AsyncSession,
            user_id: int,
    ) -> TOTPSetupResponse:
        user = await self._user_dao.get_by_id(session, user_id)
        if user is None:
            raise ValueError("用户不存在")

        if user.totp_enabled and user.totp_secret:
            raise ValueError("该账号已绑定动态口令")

        # 若已有未确认 secret 则复用，避免频繁刷新导致用户扫描失效。
        secret = user.totp_secret or pyotp.random_base32()
        uri = pyotp.TOTP(secret).provisioning_uri(
            name=user.username,
            issuer_name=settings.app_name,
        )

        await self._user_dao.update(
            session, user_id, {"totp_secret": secret, "totp_enabled": False}
        )

        security_logger.info(
            "TOTP_SETUP | user_id={} | username={}",
            user_id,
            user.username,
        )
        await self._write_log(
            session,
            event=AuthEvent.TOTP_SETUP,
            method="TOTP",
            username=user.username,
            user_id=user_id,
        )
        return TOTPSetupResponse(secret=secret, otp_auth_uri=uri)

    # ── 注册 ──────────────────────────────────────────────────────────────

    async def register(
            self,
            session: AsyncSession,
            payload: RegisterRequest,
            ip: str,
            user_agent: str,
    ) -> RegisterResponse:
        username = payload.username.strip()
        email = payload.email.strip().lower() if payload.email else None

        if await self._user_dao.get_by_username(session, username):
            raise ValueError("用户名已存在")
        if email and await self._user_dao.get_by_email(session, email):
            raise ValueError("邮箱已被注册")

        hashed_pw = _pwd_ctx.hash(payload.password)
        # 注册时直接写入 TOTP secret，保证 users 表中立即存在该用户的密钥记录。
        secret = pyotp.random_base32()
        user = User(
            username=username,
            password=hashed_pw,
            email=email,
            is_active=True,
            totp_secret=secret,
            totp_enabled=False,
            created_by=username,
            updated_by=username,
        )
        user = await self._user_dao.create(session, user)

        uri = pyotp.TOTP(secret).provisioning_uri(
            name=user.username,
            issuer_name=settings.app_name,
        )

        security_logger.info("REGISTER | username={} | ip={}", username, ip)
        await self._write_log(
            session, event=AuthEvent.TOTP_SETUP, method="REGISTER",
            username=username, user_id=user.id, ip=ip, user_agent=user_agent,
            detail="registration",
        )
        return RegisterResponse(
            user_id=user.id,
            username=user.username,
            totp_secret=secret,
            otp_auth_uri=uri,
        )

    # ── 首次绑定 TOTP 确认 ─────────────────────────────────────────────────

    async def confirm_totp(
            self,
            session: AsyncSession,
            user_id: int,
            code: str,
            ip: str,
            user_agent: str,
    ) -> TokenResponse:
        user = await self._user_dao.get_by_id(session, user_id)
        if not user or not user.totp_secret:
            raise ValueError("用户不存在或未初始化 TOTP")
        if user.totp_enabled:
            raise ValueError("TOTP 已绑定，请直接登录")

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            raise ValueError("验证码错误，请检查手机时间后重试")

        await self._user_dao.update(session, user_id, {"totp_enabled": True})

        security_logger.info("TOTP_CONFIRMED | user_id={} | username={} | ip={}", user_id, user.username, ip)
        await self._write_log(
            session, event=AuthEvent.TOTP_SETUP, method="TOTP",
            username=user.username, user_id=user_id, ip=ip, user_agent=user_agent,
            detail="confirmed",
        )
        return self.create_token(user.id, user.username)

    # ── 密码 + 动态口令 联合登录 ───────────────────────────────────────────

    async def combined_login(
            self,
            session: AsyncSession,
            payload: CombinedLoginRequest,
            ip: str,
            user_agent: str,
    ) -> TokenResponse:
        username = payload.username.strip()

        # 速率限制（复用 TOTP 失败计数器）
        await self._check_rate_limit(session, username, ip, user_agent)

        user = await self._user_dao.get_by_username(session, username)
        if not user or not user.is_active or not user.password:
            await self._write_failure(
                session, username, "PASSWORD+TOTP", ip, user_agent, "User not found or no password"
            )
            security_logger.warning("LOGIN_FAILED | username={} | method=COMBINED | ip={}", username, ip)
            raise ValueError("用户名或密码错误")

        if not _pwd_ctx.verify(payload.password, user.password):
            await self._write_failure(
                session, username, "PASSWORD+TOTP", ip, user_agent, "Invalid password", user.id
            )
            security_logger.warning("LOGIN_FAILED | username={} | method=COMBINED | ip={}", username, ip)
            raise ValueError("用户名或密码错误")

        # 强制动态口令：未绑定时先引导绑定。
        if not user.totp_secret or not user.totp_enabled:
            await self._write_log(
                session,
                event=AuthEvent.TOTP_SETUP,
                method="PASSWORD+TOTP",
                username=username,
                user_id=user.id,
                ip=ip,
                user_agent=user_agent,
                detail="totp_setup_required",
            )
            raise AuthFlowError(
                status_code=428,
                detail={
                    "code": "TOTP_SETUP_REQUIRED",
                    "message": "该账号尚未绑定动态口令，请先扫码绑定",
                    "user_id": user.id,
                    "username": user.username,
                },
            )

        totp_code = (payload.totp_code or "").strip()
        if not totp_code:
            raise ValueError("动态口令为必填项，请输入 6 位验证码")
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            failure_count = await self._log_and_count_failure(
                session, username, user.id, "TOTP", ip, user_agent
            )
            remaining = settings.totp_max_failures - failure_count
            security_logger.warning(
                "TOTP_FAILED | username={} | ip={} | failures={}/{}",
                username, ip, failure_count, settings.totp_max_failures,
            )
            if remaining <= 0:
                raise ValueError(f"令牌错误，账户已临时锁定 {settings.totp_lockout_seconds} 秒，请稍后重试")
            raise ValueError(f"动态令牌错误，还有 {remaining} 次尝试机会")

        await self._write_log(
            session, event=AuthEvent.LOGIN_SUCCESS, method="PASSWORD+TOTP",
            username=username, user_id=user.id, ip=ip, user_agent=user_agent,
        )
        security_logger.info("LOGIN_SUCCESS | username={} | method=PASSWORD+TOTP | ip={}", username, ip)
        return self.create_token(user.id, user.username)

    # ── 密码登录（保留向后兼容）──────────────────────────────────────────────

    async def password_login(
            self,
            session: AsyncSession,
            payload: PasswordLoginRequest,
            ip: str,
            user_agent: str,
    ) -> TokenResponse:
        username = payload.username.strip()

        user = await self._user_dao.get_by_username(session, username)
        if user is None or not user.is_active or not user.password:
            await self._write_failure(
                session, username, "PASSWORD", ip, user_agent, "User not found or no password"
            )
            security_logger.warning(
                "LOGIN_FAILED | username={} | method=PASSWORD | ip={}", username, ip
            )
            raise ValueError("用户名或密码错误")

        if not _pwd_ctx.verify(payload.password, user.password):
            await self._write_failure(
                session, username, "PASSWORD", ip, user_agent, "Invalid password", user.id
            )
            security_logger.warning(
                "LOGIN_FAILED | username={} | method=PASSWORD | ip={}", username, ip
            )
            raise ValueError("用户名或密码错误")

        await self._write_log(
            session,
            event=AuthEvent.LOGIN_SUCCESS,
            method="PASSWORD",
            username=username,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )
        security_logger.info(
            "LOGIN_SUCCESS | username={} | method=PASSWORD | ip={}", username, ip
        )
        return self.create_token(user.id, user.username)

    # ── TOTP 登录 ─────────────────────────────────────────────────────────────

    async def totp_login(
            self,
            session: AsyncSession,
            payload: TOTPLoginRequest,
            ip: str,
            user_agent: str,
    ) -> TokenResponse:
        username = payload.username.strip()

        # 1. 速率限制检查
        await self._check_rate_limit(session, username, ip, user_agent)

        # 2. 查找用户
        user = await self._user_dao.get_by_username(session, username)
        if user is None or not user.is_active or not user.totp_enabled or not user.totp_secret:
            await self._write_failure(session, username, "TOTP", ip, user_agent,
                                      "User not found or TOTP not configured")
            raise ValueError("用户名或令牌错误")

        # 3. 校验 TOTP（valid_window=1 允许前后 30 秒的时钟偏差）
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(payload.code, valid_window=1):
            failure_count = await self._log_and_count_failure(
                session, username, user.id, "TOTP", ip, user_agent
            )
            remaining = settings.totp_max_failures - failure_count
            security_logger.warning(
                "TOTP_FAILED | username={} | ip={} | failures={}/{}",
                username, ip, failure_count, settings.totp_max_failures,
            )
            if remaining <= 0:
                raise ValueError(
                    f"令牌错误，账户已临时锁定 {settings.totp_lockout_seconds} 秒，请稍后重试"
                )
            raise ValueError(f"令牌错误，还有 {remaining} 次尝试机会")

        # 4. 登录成功
        await self._write_log(
            session,
            event=AuthEvent.LOGIN_SUCCESS,
            method="TOTP",
            username=username,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )
        security_logger.info(
            "LOGIN_SUCCESS | username={} | method=TOTP | ip={}",
            username, ip,
        )
        return self.create_token(user.id, user.username)

    # ── GitHub OAuth2 ─────────────────────────────────────────────────────────
    @staticmethod
    def _resolve_github_redirect_uri() -> str:
        redirect_uri = (settings.github_redirect_uri or "").strip()
        if not redirect_uri:
            raise ValueError("GitHub OAuth 未配置回调地址")

        if "//" not in redirect_uri:
            raise ValueError("GitHub OAuth 回调地址格式不正确")

        if redirect_uri.endswith("/"):
            redirect_uri = redirect_uri[:-1]

        callback_path = "/api/v1/auth/github/callback"
        if not redirect_uri.endswith(callback_path):
            redirect_uri = f"{redirect_uri}{callback_path}"
        return redirect_uri

    @staticmethod
    def get_github_auth_url(state: str) -> str:
        if not settings.github_client_id or not settings.github_client_secret:
            raise ValueError("GitHub OAuth 未正确配置")

        query = urlencode(
            {
                "client_id": settings.github_client_id,
                "redirect_uri": AuthService._resolve_github_redirect_uri(),
                "scope": "user:email",
                "state": state,
            }
        )
        return f"https://github.com/login/oauth/authorize?{query}"

    async def github_callback(
            self,
            session: AsyncSession,
            code: str,
            ip: str,
            user_agent: str,
    ) -> TokenResponse:
        if not settings.github_client_id or not settings.github_client_secret:
            raise ValueError("GitHub OAuth 未正确配置")

        redirect_uri = self._resolve_github_redirect_uri()

        # 1. 用 code 换取 access_token
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            gh_access_token = token_resp.json().get("access_token")
            if not gh_access_token:
                raise ValueError("GitHub OAuth 授权码无效或已过期")

            # 2. 获取 GitHub 用户信息
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {gh_access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            user_resp.raise_for_status()
            gh_info = user_resp.json()

        gh_id = str(gh_info["id"])
        gh_login: str = gh_info["login"]
        gh_email: Optional[str] = gh_info.get("email")

        # 3. 查找或创建用户
        user = await self._user_dao.get_by_field(session, "github_id", gh_id)
        if user is None:
            username = await self._build_unique_github_username(session, gh_login)
            user = User(
                username=username,
                github_id=gh_id,
                email=gh_email,
                is_active=True,
                created_by="github_oauth",
                updated_by="github_oauth",
            )
            user = await self._user_dao.create(session, user)
            logger.info("New GitHub user created | username={} | github_id={}", user.username, gh_id)

        await self._write_log(
            session,
            event=AuthEvent.GITHUB_LOGIN,
            method="GITHUB",
            username=user.username,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
            detail=f"github_login={gh_login}",
        )
        security_logger.info(
            "GITHUB_LOGIN | username={} | github_login={} | ip={}",
            user.username, gh_login, ip,
        )
        return self.create_token(user.id, user.username)

    async def _build_unique_github_username(self, session: AsyncSession, gh_login: str) -> str:
        base = f"gh_{gh_login}"
        username = base
        suffix = 1
        while await self._user_dao.get_by_username(session, username):
            suffix += 1
            username = f"{base}_{suffix}"
        return username

    # ── 私有辅助 ─────────────────────────────────────────────────────────────

    async def _check_rate_limit(
            self,
            session: AsyncSession,
            username: str,
            ip: str,
            user_agent: str,
    ) -> None:
        """如果近期失败次数 >= 上限则拒绝，并计算剩余等待时间。"""
        failure_count = await self._log_dao.count_recent_failures(
            session,
            username=username,
            event=AuthEvent.TOTP_FAILED,
            window_seconds=settings.totp_lockout_seconds,
        )
        if failure_count < settings.totp_max_failures:
            return

        # 计算距第一次失败还剩多少秒
        last_time = await self._log_dao.get_last_failure_time(
            session, username=username, event=AuthEvent.TOTP_FAILED
        )
        wait_secs = settings.totp_lockout_seconds
        if last_time:
            elapsed = (datetime.now(UTC).replace(tzinfo=None) - last_time).total_seconds()
            wait_secs = max(0, int(settings.totp_lockout_seconds - elapsed))

        await self._write_log(
            session,
            event=AuthEvent.TOTP_LOCKED,
            method="TOTP",
            username=username,
            ip=ip,
            user_agent=user_agent,
            detail=f"rate_limited failures={failure_count}",
        )
        security_logger.warning(
            "TOTP_LOCKED | username={} | ip={} | failures={} | wait={}s",
            username, ip, failure_count, wait_secs,
        )
        raise ValueError(
            f"尝试次数过多，请 {wait_secs} 秒后重试"
        )

    async def _log_and_count_failure(
            self,
            session: AsyncSession,
            username: str,
            user_id: Optional[int],
            method: str,
            ip: str,
            user_agent: str,
    ) -> int:
        """记录一次失败并返回近期总失败次数。"""
        await self._write_failure(
            session, username, method, ip, user_agent, "Invalid TOTP code", user_id
        )
        return await self._log_dao.count_recent_failures(
            session,
            username=username,
            event=AuthEvent.TOTP_FAILED,
            window_seconds=settings.totp_lockout_seconds,
        )

    async def _write_failure(
            self,
            session: AsyncSession,
            username: str,
            method: str,
            ip: str,
            user_agent: str,
            detail: str,
            user_id: Optional[int] = None,
    ) -> None:
        await self._write_log(
            session,
            event=AuthEvent.TOTP_FAILED,
            method=method,
            username=username,
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
            detail=detail,
        )

    async def _write_log(
            self,
            session: AsyncSession,
            event: str,
            method: str,
            username: str = "",
            user_id: Optional[int] = None,
            ip: str = "",
            user_agent: str = "",
            detail: Optional[str] = None,
    ) -> None:
        entry = AuthLog(
            user_id=user_id,
            username=username,
            event=event,
            method=method,
            ip_address=ip or None,
            user_agent=(user_agent[:256] if user_agent else None),
            detail=detail,
        )
        await self._log_dao.create(session, entry)
