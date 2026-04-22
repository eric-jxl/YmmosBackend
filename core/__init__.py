from core.settings import Settings, get_settings
from core.logger import setup_logging, shutdown_logging, security_logger
from core.auth_middleware import JWTAuthMiddleware, default_public_path_patterns
from core.exceptions import (
    APIException,
    AuthenticationError,
    PermissionDenied,
    ResourceNotFoundError,
    BadRequestError,
    RateLimitExceeded,
    PreconditionRequired,
    ServerError,
)
from core.crypto import (
    hash_password,
    verify_password,
    generate_totp_secret,
    create_totp_uri,
    verify_totp_code,
    generate_state_token,
    generate_jti_token,
)
from core.helpers import get_client_ip, now_utc, utc_to_datetime

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # Logging
    "setup_logging",
    "shutdown_logging",
    "security_logger",
    # Auth Middleware
    "JWTAuthMiddleware",
    "default_public_path_patterns",
    # Exceptions
    "APIException",
    "AuthenticationError",
    "PermissionDenied",
    "ResourceNotFoundError",
    "BadRequestError",
    "RateLimitExceeded",
    "PreconditionRequired",
    "ServerError",
    # Crypto
    "hash_password",
    "verify_password",
    "generate_totp_secret",
    "create_totp_uri",
    "verify_totp_code",
    "generate_state_token",
    "generate_jti_token",
    # Helpers
    "get_client_ip",
    "now_utc",
    "utc_to_datetime",
]
