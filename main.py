#!/usr/bin/env python3

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from core import (
    JWTAuthMiddleware,
    default_public_path_patterns,
    get_settings,
    setup_logging,
    shutdown_logging,
    APIException,
)
from core.exception_handlers import (
    validation_exception_handler,
    global_exception_handler,
    api_exception_handler,
)
from db import close_db, init_db
from routes import api_router
from schema.response import ApiResponse

settings = get_settings()

# 在模块加载时立即初始化日志（确保 uvicorn reload worker 也能生效）
setup_logging(
    level="DEBUG" if settings.is_development else "INFO",
    is_dev=settings.is_development,
)

templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动、关闭资源"""
    # ── 启动 ──
    logger.info("🚀 应用启动中...")
    
    # 初始化数据库
    await init_db()
    logger.info("✅ 数据库初始化完成")
    
    yield
    
    # ── 关闭 ──
    logger.info("🛑 应用关闭中...")
    
    # 关闭数据库连接（设置较短超时避免卡住）
    try:
        await asyncio.wait_for(close_db(), timeout=3.0)
        logger.info("✅ 数据库连接已关闭")
    except asyncio.TimeoutError:
        logger.warning("⚠️ 数据库关闭超时，强制继续")
    except Exception as e:
        logger.error(f"⚠️ 数据库关闭错误: {e}")
    
    # 关闭日志处理器（避免 semaphore 泄漏）
    shutdown_logging()
    
    logger.info("👋 应用已优雅退出")



app = FastAPI(
    title=settings.app_name,
    description="企业级 Restful API",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None,  # 禁用默认的 /docs，使用自定义路由
    redoc_url="/redoc",
)

app.add_middleware(
    JWTAuthMiddleware,
    secret=settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
    public_path_patterns=tuple(default_public_path_patterns()),
)

# 全局异常处理器：统一响应格式
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(APIException, api_exception_handler)

# 静态资源
app.mount("/static", StaticFiles(directory="static"), name="static")

# Route registration (managed centrally in routes)
app.include_router(api_router)


def custom_openapi():
    """自定义 OpenAPI schema，添加 Bearer token 认证方案"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description="企业级 Restful API",
        routes=app.routes,
    )
    
    # 添加 Bearer token 认证方案
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "输入你的 JWT access_token（无需添加 'Bearer ' 前缀）"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", include_in_schema=False)
async def root():
    """根路由"""
    return ApiResponse.success(data={"message": "欢迎使用 API", "docs": "/docs"})


@app.get("/health", tags=["system"])
async def health():
    return ApiResponse.success(data={"status": "ok", "version": settings.app_version})


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    """渲染企业级登录页面。"""
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "app_name": settings.app_name,
            "github_enabled": bool(
                settings.github_client_id and settings.github_client_secret and settings.github_redirect_uri
            ),
        },
    )


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def custom_swagger_ui_html():
    """自定义 Swagger UI，自动从 localStorage 注入 access_token"""
    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>""" + settings.app_name + """ - API 文档</title>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <style>
        .topbar { display: none; }
        body { margin: 0; padding: 0; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            // 从 localStorage 读取 token
            const getToken = () => localStorage.getItem('access_token');
            
            const ui = SwaggerUIBundle({
                url: "/openapi.json",
                dom_id: '#swagger-ui',
                deepLinking: true,
                persistAuthorization: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                layout: "StandaloneLayout",
                // 使用 requestInterceptor 自动添加 Authorization header
                requestInterceptor: (req) => {
                    const token = getToken();
                    if (token && !req.headers.Authorization) {
                        req.headers.Authorization = `Bearer ${token}`;
                    }
                    return req;
                },
                onComplete: function() {
                    const token = getToken();
                    if (token) {
                        // 同时也设置到 Swagger UI 的授权中，让界面显示已授权状态
                        ui.preauthorizeApiKey('Bearer', token);
                        console.log('✅ 已自动注入 access_token 到 Swagger UI');
                        
                        // 显示提示信息
                        const info = document.createElement('div');
                        info.style.cssText = 'position:fixed;top:10px;right:10px;background:#10b981;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:9999;font-size:14px;font-family:system-ui;animation:slideIn 0.3s ease-out;';
                        info.innerHTML = '🔓 已自动授权，可直接测试接口';
                        document.body.appendChild(info);
                        
                        const style = document.createElement('style');
                        style.textContent = '@keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }';
                        document.head.appendChild(style);
                        
                        setTimeout(() => {
                            info.style.transition = 'opacity 0.3s';
                            info.style.opacity = '0';
                            setTimeout(() => info.remove(), 300);
                        }, 3000);
                    } else {
                        console.warn('⚠️ 未找到 access_token，请先到 /login 登录');
                        
                        // 显示警告提示
                        const warning = document.createElement('div');
                        warning.style.cssText = 'position:fixed;top:10px;right:10px;background:#ef4444;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:9999;font-size:14px;font-family:system-ui;';
                        warning.innerHTML = '🔒 未登录，请先<a href="/login" style="color:white;text-decoration:underline;margin-left:5px;">前往登录</a>';
                        document.body.appendChild(warning);
                    }
                }
            });
            window.ui = ui;
        }
    </script>
</body>
</html>
        """,
        status_code=200
    )


if __name__ == "__main__":
    effective_reload = settings.app_reload and settings.is_development

    run_kwargs: dict = {
        "app": "main:app",
        "host": settings.app_host,
        "port": settings.app_port,
        "reload": effective_reload,
        "log_level": "debug" if settings.is_development else "info",
        "timeout_graceful_shutdown": 5,  # 优雅关闭超时时间（秒）
    }
    # reload 模式下 uvicorn 会忽略 workers，这里显式避免该冲突。
    if not effective_reload:
        run_kwargs["workers"] = settings.app_workers

    try:
        uvicorn.run(**run_kwargs)
    except KeyboardInterrupt:
        logger.info("⌨️  收到键盘中断，正在退出...")
    finally:
        logger.info("🏁 服务器已停止")
