#!/usr/bin/env bash
# Logical backup of the DeVault control-plane PostgreSQL database (metadata only).
# See website/docs/install/control-plane-database-dr.md
set -euo pipefail

OUTPUT=""
COMPOSE_DIR=""
PROJECT_FILE="docker-compose.yml"

usage() {
  cat <<'EOF'
用法: control-plane-pg-backup.sh -o <文件.dump> [--compose-dir <deploy 目录>]

将控制面元数据库导出为 PostgreSQL 自定义格式（-Fc），可用 pg_restore 恢复。

直连数据库（本机已安装 pg_dump，使用 libpq 环境变量）:
  PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE
  默认值: PGHOST=127.0.0.1 PGPORT=5432 PGUSER=devault PGDATABASE=devault

经 Docker Compose（在 deploy 目录下使用仓库自带 postgres 服务名）:
  ./control-plane-pg-backup.sh -o ./backups/devault.dump --compose-dir /path/to/deploy

示例（仓库根目录）:
  ./deploy/scripts/control-plane-pg-backup.sh -o ./backups/cp-$(date +%Y%m%d-%H%M%S).dump \\
    --compose-dir ./deploy
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      OUTPUT=${2:-}
      shift 2
      ;;
    --compose-dir)
      COMPOSE_DIR=${2:-}
      shift 2
      ;;
    -f|--file)
      PROJECT_FILE=${2:-}
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$OUTPUT" ]]; then
  echo "错误: 必须指定 -o/--output" >&2
  usage >&2
  exit 1
fi

out_dir=$(dirname "$OUTPUT")
mkdir -p "$out_dir"

PGUSER="${PGUSER:-devault}"
PGDATABASE="${PGDATABASE:-devault}"

if [[ -n "$COMPOSE_DIR" ]]; then
  if [[ ! -d "$COMPOSE_DIR" ]]; then
    echo "错误: --compose-dir 不是目录: $COMPOSE_DIR" >&2
    exit 1
  fi
  compose_file="$COMPOSE_DIR/$PROJECT_FILE"
  if [[ ! -f "$compose_file" ]]; then
    echo "错误: 未找到 $compose_file" >&2
    exit 1
  fi
  (
    cd "$COMPOSE_DIR"
    docker compose -f "$PROJECT_FILE" exec -T postgres \
      pg_dump -U "$PGUSER" -d "$PGDATABASE" -Fc
  ) >"$OUTPUT"
else
  export PGHOST="${PGHOST:-127.0.0.1}"
  export PGPORT="${PGPORT:-5432}"
  pg_dump -U "$PGUSER" -d "$PGDATABASE" -Fc -f "$OUTPUT"
fi

bytes=$(wc -c <"$OUTPUT" | tr -d ' ')
echo "已写入 $OUTPUT (${bytes} 字节)"
