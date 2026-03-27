#!/bin/bash

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== YmmosBackend Docker 构建脚本 ===${NC}\n"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请访问 https://docs.docker.com/get-docker/ 安装 Docker"
    exit 1
fi

# 检查必要文件
if [ ! -f "pyproject.toml" ] || [ ! -f "uv.lock" ]; then
    echo -e "${RED}错误: 找不到 pyproject.toml 或 uv.lock${NC}"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

# 构建镜像
echo -e "${YELLOW}正在构建 Docker 镜像...${NC}"
docker build -t ymmosbackend:latest . || {
    echo -e "${RED}构建失败${NC}"
    exit 1
}

echo -e "${GREEN}✓ 镜像构建成功${NC}\n"

# 询问是否运行容器
read -p "是否立即运行容器? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}启动容器...${NC}"

    # 创建必要的目录
    mkdir -p data logs

    # 运行容器
    docker run -d \
        --name ymmosbackend \
        -p 8000:8000 \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        -e JWT_SECRET_KEY="${JWT_SECRET_KEY:-dev-secret-key-please-change}" \
        ymmosbackend:latest || {
        echo -e "${RED}容器启动失败${NC}"
        exit 1
    }

    echo -e "${GREEN}✓ 容器已启动${NC}"
    echo -e "\n访问应用:"
    echo -e "  - API 文档: ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  - ReDoc: ${GREEN}http://localhost:8000/redoc${NC}"
    echo -e "\n查看日志: ${YELLOW}docker logs -f ymmosbackend${NC}"
    echo -e "停止容器: ${YELLOW}docker stop ymmosbackend${NC}"
    echo -e "删除容器: ${YELLOW}docker rm ymmosbackend${NC}"
fi

echo -e "\n${GREEN}完成!${NC}"

