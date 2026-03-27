# Ymmos Backend

企业级 **FastAPI + SQLModel** 后端项目，采用标准分层架构 `model/dao/service/routes`，集成完整的认证授权、日志审计、优雅退出等生产级特性。

## ✨ 核心特性

- 🏗️ **分层架构**：Model/DAO/Service/Routes 清晰职责分离
- 🔐 **认证授权**：JWT + 密码哈希 + TOTP 双因素 + GitHub OAuth2
- 📝 **统一日志**：Loguru 分级日志（应用/错误/安全审计）+ 日志轮转
- 🗄️ **多数据库支持**：SQLite / MySQL / PostgreSQL 异步连接池
- 🛡️ **安全审计**：登录日志 + TOTP 失败锁定 + 独立安全审计日志
- 🎯 **统一响应**：标准化 API 响应格式（ApiResponse）
- 🚦 **优雅退出**：信号处理 + 资源清理 + 无泄漏警告
- 📚 **自动文档**：Swagger UI + 自动 Token 注入
- 🎨 **企业登录页**：集成 TOTP QR 码生成 + GitHub OAuth

## 📂 项目结构

```text
YmmosBackend/
├── main.py                      # 应用入口
├── pyproject.toml              # 项目依赖与配置
├── .env.example                # 环境变量模板
├── test_graceful_shutdown.py   # 优雅退出测试
│
├── core/                       # 核心配置与中间件
│   ├── settings.py            # 全局配置（pydantic-settings）
│   ├── logger.py              # Loguru 日志配置
│   ├── auth_middleware.py     # JWT 认证中间件
│   └── exception_handlers.py  # 全局异常处理
│
├── db/                         # 数据库管理
│   └── session.py             # 异步连接池 + 会话注入 + 迁移
│
├── model/                      # 数据模型（SQLModel）
│   ├── base.py                # 基础模型（审计字段）
│   ├── user.py                # 用户模型
│   └── auth_log.py            # 认证日志模型
│
├── schema/                     # 请求/响应模型（Pydantic）
│   ├── response.py            # 统一响应格式
│   ├── user.py                # 用户 Schema
│   └── auth.py                # 认证 Schema
│
├── dao/                        # 数据访问层
│   ├── base.py                # 通用 CRUD + 组合查询
│   ├── user_dao.py            # 用户数据访问
│   └── auth_log_dao.py        # 认证日志访问
│
├── service/                    # 业务逻辑层
│   ├── user_service.py        # 用户业务逻辑
│   └── auth_service.py        # 认证业务逻辑
│
├── routes/                     # API 路由层
│   ├── user_route.py          # 用户 API
│   └── auth_route.py          # 认证 API
│
├── templates/                  # Jinja2 模板
│   └── login.html             # 企业登录页
│
├── static/                     # 静态资源
├── logs/                       # 日志文件目录
└── docs/                       # 项目文档
    └── GRACEFUL_SHUTDOWN.md   # 优雅退出机制文档
```

## 🏛️ 分层职责

| 层级 | 职责 | 示例 |
|------|------|------|
| **Model** | 数据表模型 + 审计字段 | `User`, `AuthLog` |
| **Schema** | API 请求/响应模型 | `UserCreate`, `LoginRequest` |
| **DAO** | 通用 CRUD + 复杂查询（过滤/模糊/分页） | `UserDAO.find_by_email()` |
| **Service** | 业务逻辑 + 数据校验 | 密码验证、TOTP 生成 |
| **Routes** | HTTP 路由 + 异常处理 | `/api/v1/users` |

## ⚙️ 配置说明

项目使用 `pydantic-settings`，从 `.env` 文件加载配置（参考 `.env.example`）。

### 主要配置项

```bash
# ─── 应用配置 ───
APP_ENV=development              # 环境：development/production
APP_NAME=Backend                # 应用名称
APP_HOST=0.0.0.0                # 监听地址
APP_PORT=8000                   # 监听端口
APP_RELOAD=true                 # 热重载（仅开发环境）
APP_WORKERS=4                   # Worker 数量（生产环境）

# ─── 数据库配置 ───
# 选择一种数据库（SQLite/MySQL/PostgreSQL）
DATABASE_URL=sqlite+aiosqlite:///sqlmodel.db
# DATABASE_URL=mysql+asyncmy://user:password@localhost:3306/db?charset=utf8mb4
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/db

DB_ECHO=false                   # SQL 日志
DB_POOL_SIZE=20                 # 连接池大小
DB_MAX_OVERFLOW=10              # 最大溢出连接
DB_POOL_RECYCLE=3600            # 连接回收时间（秒）
DB_POOL_TIMEOUT=30              # 连接超时（秒）

# ─── JWT 配置 ───
JWT_SECRET=your-secret-key      # JWT 密钥（生产环境必须修改）
JWT_ALGORITHM=HS256             # 加密算法
JWT_EXPIRE_MINUTES=1440         # Token 有效期（分钟）

# ─── GitHub OAuth ───
GITHUB_CLIENT_ID=xxx            # GitHub OAuth Client ID
GITHUB_CLIENT_SECRET=xxx        # GitHub OAuth Client Secret
GITHUB_REDIRECT_URI=https://api.ymmos.com/api/v1/auth/github/callback

# ─── TOTP 配置 ───
TOTP_MAX_FAILURES=3             # TOTP 最大失败次数
TOTP_LOCKOUT_SECONDS=60         # 锁定时长（秒）
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，修改必要的配置
```

### 3. 初始化数据库

```bash
# 初始化表结构和管理员账户
python init_users_sqlite.py
```

### 4. 启动服务

```bash
python main.py
```

服务启动后访问：
- 🌐 **API 文档**: http://localhost:8000/docs
- 🔐 **登录页**: http://localhost:8000/login
- ❤️ **健康检查**: http://localhost:8000/health

## 📡 API 端点

### 系统接口

- `GET /` - 欢迎页
- `GET /health` - 健康检查
- `GET /docs` - Swagger UI（自动 Token 注入）
- `GET /redoc` - ReDoc 文档
- `GET /login` - 企业登录页

### 认证接口 (`/api/v1/auth`)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/login` | 用户登录（密码） | ❌ |
| POST | `/register` | 用户注册 | ❌ |
| POST | `/logout` | 用户登出 | ✅ |
| GET | `/me` | 获取当前用户信息 | ✅ |
| POST | `/totp/setup` | 设置 TOTP | ✅ |
| POST | `/totp/verify` | 验证 TOTP | ✅ |
| POST | `/totp/login` | TOTP 登录 | ❌ |
| GET | `/github` | GitHub OAuth 跳转 | ❌ |
| GET | `/github/callback` | GitHub OAuth 回调 | ❌ |

### 用户接口 (`/api/v1/users`)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/` | 获取用户列表（支持组合查询） | ✅ |
| GET | `/{user_id}` | 获取用户详情 | ✅ |
| POST | `/` | 创建用户 | ✅ |
| PUT | `/{user_id}` | 更新用户 | ✅ |
| DELETE | `/{user_id}` | 删除用户 | ✅ |

#### 用户列表查询参数

```bash
GET /api/v1/users?keyword=admin&created_by=system&start_at=2024-01-01&limit=20
```

支持参数：
- `keyword` - 关键词（模糊搜索用户名/邮箱）
- `created_by` - 创建人
- `start_at` - 开始时间
- `end_at` - 结束时间
- `skip` - 跳过记录数（分页）
- `limit` - 返回记录数（分页）

## 🔐 认证流程

### 1. 密码登录

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

响应：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer"
  }
}
```

### 2. 使用 Token

在请求头中添加：
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 3. TOTP 双因素认证

```bash
# 1. 设置 TOTP
POST /api/v1/auth/totp/setup

# 2. 扫描 QR 码并验证
POST /api/v1/auth/totp/verify
{
  "code": "123456"
}

# 3. 使用 TOTP 登录
POST /api/v1/auth/totp/login
{
  "email": "admin@example.com",
  "totp_code": "123456"
}
```

### 4. GitHub OAuth 登录

访问：`http://localhost:8000/api/v1/auth/github`

## 📊 日志系统

项目使用 Loguru 实现分级日志管理：

```
logs/
├── app_2026-03-28.log          # 应用日志（INFO+，保留 30 天）
├── error_2026-03-28.log        # 错误日志（ERROR+，保留 90 天）
└── security_2026-03-28.log     # 安全审计（保留 365 天）
```

### 日志特性

- ✅ 按日期自动轮转
- ✅ 自动压缩归档（gzip）
- ✅ 分级日志（DEBUG/INFO/ERROR）
- ✅ 安全事件独立记录
- ✅ 完整的调用栈追踪

### 记录安全事件

```python
from core import security_logger

security_logger.info(f"用户登录成功 | user_id={user.id} | ip={ip_address}")
```

## 🛡️ 安全特性

### 1. 密码安全
- ✅ bcrypt 哈希存储
- ✅ 密码强度验证
- ✅ 自动加盐

### 2. TOTP 双因素认证
- ✅ 基于时间的一次性密码
- ✅ QR 码生成
- ✅ 失败次数限制 + 自动锁定

### 3. JWT Token
- ✅ HS256 签名
- ✅ 过期时间控制
- ✅ 无状态认证

### 4. 认证日志
- ✅ 记录所有登录/登出事件
- ✅ IP 地址追踪
- ✅ 失败原因记录
- ✅ 独立安全审计日志

## 🎯 优雅退出机制

项目实现了完整的优雅退出机制，确保无资源泄漏：

✅ **信号处理**：捕获 SIGINT/SIGTERM  
✅ **数据库清理**：正确关闭连接池  
✅ **日志完整性**：确保所有日志写入  
✅ **无泄漏警告**：正确清理 semaphore 资源  

详细文档：[docs/GRACEFUL_SHUTDOWN.md](docs/GRACEFUL_SHUTDOWN.md)

测试优雅退出：
```bash
python test_graceful_shutdown.py
```

## 📝 审计字段

所有继承 `BaseModel` 的模型自动具备审计字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `created_by` | VARCHAR(64) | 创建人 |
| `updated_by` | VARCHAR(64) | 修改人 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 修改时间 |

使用示例：
```python
from model.base import BaseModel

class YourModel(BaseModel, table=True):
    __tablename__ = "your_table"
    # 自动包含审计字段
```

## 🧪 测试

```bash
# 测试优雅退出
python test_graceful_shutdown.py

# 初始化测试数据
python init_users_sqlite.py
```

## 🚀 生产部署

### 1. 修改配置

```bash
# .env
APP_ENV=production
APP_RELOAD=false
APP_WORKERS=4
JWT_SECRET=<使用强随机密钥>
DATABASE_URL=<生产数据库连接>
```

### 2. 使用多 Worker 启动

```bash
# 方式 1：使用内置配置
python main.py

# 方式 2：直接使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. 使用 Systemd

创建 `/etc/systemd/system/ymmos-backend.service`:

```ini
[Unit]
Description=Ymmos Backend Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/YmmosBackend
Environment="PATH=/path/to/.venv/bin"
ExecStart=/path/to/.venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable ymmos-backend
sudo systemctl start ymmos-backend
sudo systemctl status ymmos-backend
```

## 📚 技术栈

- **Web 框架**: FastAPI 0.135+
- **ORM**: SQLModel 0.0.37+
- **异步数据库**: SQLAlchemy 2.0+ (async)
- **数据库驱动**: aiosqlite / asyncmy / asyncpg
- **配置管理**: pydantic-settings
- **日志**: Loguru
- **认证**: PyJWT + passlib[bcrypt]
- **双因素认证**: pyotp
- **HTTP 客户端**: httpx
- **模板引擎**: Jinja2
- **服务器**: Uvicorn

## 📖 延伸阅读

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLModel 官方文档](https://sqlmodel.tiangolo.com/)
- [Loguru 文档](https://loguru.readthedocs.io/)
- [优雅退出机制详解](docs/GRACEFUL_SHUTDOWN.md)

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

⭐ **如果这个项目对你有帮助，请给个 Star！**

