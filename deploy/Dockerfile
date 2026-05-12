# 单源依赖：仅从 pyproject.toml 安装。
# pip 缓存需 BuildKit：`DOCKER_BUILDKIT=1 docker build -f deploy/Dockerfile .` 或 `make docker-build`（Docker Desktop 默认已开启）
# 默认 PyPI 镜像：阿里云；覆盖：`docker build --build-arg PIP_INDEX_URL=https://pypi.org/simple/ ...`
FROM python:3.12-slim

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY pyproject.toml README.md alembic.ini /app/
COPY alembic /app/alembic
COPY src /app/src
COPY deploy/scripts /app/deploy/scripts
RUN chmod +x /app/deploy/scripts/pgbackrest_demo_stanza_init.sh

# pgBackRest CLI for edge Agent physical-backup jobs and demo-stack stanza init (bookworm package; demo + CI image).
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends pgbackrest openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel \
    && pip install -e .

EXPOSE 8000
EXPOSE 50051
