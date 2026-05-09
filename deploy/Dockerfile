# 单源依赖：仅从 pyproject.toml 安装。
# pip 缓存需 BuildKit：`DOCKER_BUILDKIT=1 docker build -f deploy/Dockerfile .` 或 `make docker-build`（Docker Desktop 默认已开启）
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY pyproject.toml README.md alembic.ini /app/
COPY alembic /app/alembic
COPY src /app/src

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel \
    && pip install -e .

EXPOSE 8000
EXPOSE 50051
