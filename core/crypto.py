"""
加密工具函数：密码哈希、TOTP、随机令牌等。
集中管理所有加密相关配置，避免在各 service 中重复定义。
"""
import secrets
from typing import Optional

import pyotp
from passlib.context import CryptContext

# 全局密码哈希上下文（scrypt 算法）
pwd_context = CryptContext(schemes=["scrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """密码哈希。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码。"""
    return pwd_context.verify(plain_password, hashed_password)


def generate_totp_secret() -> str:
    """生成 TOTP 密钥。"""
    return pyotp.random_base32()


def create_totp_uri(secret: str, username: str, issuer_name: str) -> str:
    """创建 TOTP provisioning URI (用于生成二维码)。"""
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer_name)


def verify_totp_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """验证 TOTP 验证码。"""
    return pyotp.TOTP(secret).verify(code, valid_window=valid_window)


def generate_state_token() -> str:
    """生成 OAuth state 令牌。"""
    return secrets.token_urlsafe(16)


def generate_jti_token() -> str:
    """生成 JWT 唯一标识（防重放）。"""
    return secrets.token_hex(16)
