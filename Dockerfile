# Dockerfile for pr-genius MCP server — v1.9.0 Glama deploy
# 克莱恩 2026-07-19 M4 指示

FROM python:3.12-slim

# 标签 — 给 Glama 目录展示用
LABEL maintainer="zsxh1990 <445655361@qq.com>"
LABEL project="pr-genius"
LABEL version="1.9.0"
LABEL description="Evidence-backed PR contribution advisor MCP — local-only, read-only, OKF v0.1 compliant"
LABEL license="MIT"

# 安全 + 体积优化
RUN groupadd -r prgenius && useradd -r -g prgenius prgenius && \
    apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制所有需要的文件（.dockerignore 控制排除项）
COPY . .

# 装 prgenius-core
RUN pip install --no-cache-dir ./prgenius

# 装 MCP extras
RUN pip install --no-cache-dir "mcp>=1.0,<3.0"

# 安全 + 只读
USER prgenius

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -m prgenius --version || exit 1

# 入口: stdio MCP server
ENTRYPOINT ["python", "-m", "prgenius", "mcp", "serve"]