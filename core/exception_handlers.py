"""
全局异常处理器：统一响应格式。
"""
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from schema.response import ApiResponse


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTPException，转为统一格式。"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(
            msg=str(exc.detail) if isinstance(exc.detail, str) else "请求错误",
            code=exc.status_code,
            data=exc.detail if not isinstance(exc.detail, str) else None,
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理 Pydantic 参数校验异常，转为统一格式。"""
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    field = " -> ".join(str(loc) for loc in first_error.get("loc", []))
    msg_detail = first_error.get("msg", "参数校验失败")
    msg = f"{field}: {msg_detail}" if field else msg_detail

    logger.warning(
        "VALIDATION_ERROR | path={} | errors={}",
        request.url.path,
        errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiResponse.error(
            msg=msg,
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            data={"errors": errors},
        ).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获所有未处理的异常，转为统一格式。"""
    logger.exception(
        "UNHANDLED_EXCEPTION | path={} | method={} | exc={}",
        request.url.path,
        request.method,
        exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            msg="服务器内部错误，请稍后重试",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ).model_dump(),
    )

