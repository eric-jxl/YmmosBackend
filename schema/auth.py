from typing import Optional
from sqlmodel import SQLModel


class CombinedLoginRequest(SQLModel):
    """用户名 + 密码 + 可选动态口令，三合一登录。"""
    username: str
    password: str
    totp_code: Optional[str] = None   # TOTP 已绑定时必填


class PasswordLoginRequest(SQLModel):
    """用户名 + 密码登录请求（保留向后兼容）。"""
    username: str
    password: str


class TOTPLoginRequest(SQLModel):
    """TOTP 登录请求。"""
    username: str
    code: str  # 6 位动态令牌


class TOTPSetupResponse(SQLModel):
    """TOTP 初始化响应（返回给用户扫码）。"""
    secret: str          # base32 密钥，供手动录入
    otp_auth_uri: str    # otpauth:// URI，供 App 扫码


class TokenResponse(SQLModel):
    """JWT 令牌响应。"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int      # 秒


class GithubLoginUrlResponse(SQLModel):
    """GitHub OAuth 授权跳转 URL。"""
    redirect_url: str


class RegisterRequest(SQLModel):
    """注册请求。"""
    username: str
    password: str
    email: Optional[str] = None


class RegisterResponse(SQLModel):
    """注册成功响应，同时下发 TOTP 绑定信息。"""
    user_id: int
    username: str
    totp_secret: str
    otp_auth_uri: str


class TOTPConfirmRequest(SQLModel):
    """首次绑定 TOTP：提交 App 显示的验证码。"""
    code: str
