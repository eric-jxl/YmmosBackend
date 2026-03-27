# Docker 和 CI/CD 配置说明

## 📦 Dockerfile 说明

本项目使用 **uv** 作为依赖管理工具，采用多阶段构建优化镜像大小。

### 构建特点
- **Stage 1 (builder)**: 使用 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` 基础镜像，通过 uv 安装依赖
- **Stage 2 (runtime)**: 使用精简的 `python:3.12-slim` 镜像，只复制必要的虚拟环境和应用代码
- **优化特性**:
  - 启用字节码预编译 (`UV_COMPILE_BYTECODE=1`)
  - 使用 `--frozen` 确保依赖版本锁定
  - 多阶段构建减少最终镜像大小

### 本地构建镜像

```bash
# 构建镜像
docker build -t ymmosbackend:latest .

# 运行容器
docker run -p 8000:8000 ymmosbackend:latest

# 带环境变量运行
docker run -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./sqlmodel.db \
  -e JWT_SECRET_KEY=your-secret-key \
  ymmosbackend:latest
```

### Docker Compose 示例

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./sqlmodel.db
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

## 🚀 GitHub Actions CI/CD

项目配置了自动化的 Docker 镜像构建和推送流程。

### 触发条件
- **Push 到 main/master 分支**: 自动构建并推送镜像
- **创建 tag (v*)**: 按版本号构建发布镜像
- **Pull Request**: 构建但不推送（验证构建成功）
- **手动触发**: 通过 GitHub Actions 界面手动运行

### 镜像标签策略
自动生成以下标签：
- `latest` - 最新的 main/master 分支版本
- `{branch}` - 分支名称
- `v{version}` - 语义化版本号（从 git tag）
- `{branch}-{sha}` - 分支 + commit SHA

### 使用 GitHub Container Registry

镜像推送到 `ghcr.io/{username}/{repo}`

```bash
# 登录 GitHub Container Registry
echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin

# 拉取镜像
docker pull ghcr.io/{username}/ymmosbackend:latest

# 运行镜像
docker run -p 8000:8000 ghcr.io/{username}/ymmosbackend:latest
```

### 配置说明

1. **无需额外配置**: GitHub Actions 使用内置的 `GITHUB_TOKEN`，无需额外设置密钥
2. **权限**: workflow 自动获得推送包的权限
3. **多平台构建**: 支持 `linux/amd64` 和 `linux/arm64`
4. **构建缓存**: 使用 GitHub Actions Cache 加速构建

### 发布新版本

```bash
# 创建并推送 tag
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions 将自动构建并推送以下标签的镜像：
# - ghcr.io/{username}/ymmosbackend:v1.0.0
# - ghcr.io/{username}/ymmosbackend:1.0
# - ghcr.io/{username}/ymmosbackend:1
# - ghcr.io/{username}/ymmosbackend:latest
```

## 🔧 环境变量

应用支持以下环境变量（在 `core/settings.py` 中定义）：

```bash
# 数据库
DATABASE_URL=sqlite:///./sqlmodel.db

# JWT 认证
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用配置
DEBUG=false
LOG_LEVEL=INFO
```

## 📝 最佳实践

1. **开发环境**: 使用 `uv` 本地管理依赖
   ```bash
   uv sync
   uv run uvicorn main:app --reload
   ```

2. **生产部署**: 使用 Docker 镜像
3. **版本管理**: 使用语义化版本号标签
4. **安全**: 通过环境变量或 secrets 管理敏感信息

## 🐛 故障排查

### 构建失败
- 确保 `pyproject.toml` 和 `uv.lock` 已提交
- 检查依赖是否有冲突
- 查看 GitHub Actions 日志

### 运行失败
- 检查环境变量是否正确设置
- 查看容器日志: `docker logs <container_id>`
- 确保端口 8000 未被占用

### 权限问题
- 确保 GitHub Actions 有 packages: write 权限
- 检查仓库设置中的 Actions 权限配置

