# Build from repository iam/ directory (context = iam/).
FROM python:3.12-slim

# 默认 apt：阿里云 Debian 镜像
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|https://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources; \
      sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources; \
      sed -i 's|https://deb.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
      sed -i 's|http://deb.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; \
      sed -i 's|security.debian.org/debian-security|mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list; \
    fi

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel \
    && pip install -e .

EXPOSE 8100

CMD ["uvicorn", "devault_iam.api.main:app", "--host", "0.0.0.0", "--port", "8100"]
