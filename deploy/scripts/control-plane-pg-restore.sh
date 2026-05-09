#!/usr/bin/env bash
# Restore control-plane PostgreSQL from a custom-format (-Fc) pg_dump.
# See website/docs/install/control-plane-database-dr.md
set -euo pipefail

INPUT=""
COMPOSE_DIR=""
PROJECT_FILE="docker-compose.yml"
RESTART_SERVICES="0"

usage() {
  cat <<'EOF'
用法: control-plane-pg-restore.sh -i <文件.dump> [--compose-dir <deploy 目录>] [--restart-services]

从自定义格式 logical dump 恢复控制面元数据库。此操作会覆盖当前库中的对象，请先停止写入者或接受短暂停机。

安全第一 — 必须设置环境变量:
  DEVAULT_PG_RESTORE_CONFIRM=yes

可选:
  --restart-services  若提供 --compose-dir，则在恢复前 stop api/scheduler、结束后 start（减少连接占用）

经 Compose 时会把 dump 拷入 postgres 容器再执行 pg_restore（自定义格式不可可靠地经管道 stdin）。

环境变量（直连模式）:
  PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE（默认 devault）

示例:
  DEVAULT_PG_RESTORE_CONFIRM=yes \\
    ./deploy/scripts/control-plane-pg-restore.sh -i ./backups/devault.dump --compose-dir ./deploy \\
    --restart-services
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input)
      INPUT=${2:-}
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
    --restart-services)
      RESTART_SERVICES="1"
      shift
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

if [[ "${DEVAULT_PG_RESTORE_CONFIRM:-}" != "yes" ]]; then
  echo "拒绝执行: 请设置 DEVAULT_PG_RESTORE_CONFIRM=yes 表明你已阅读 Runbook 并确认目标实例。" >&2
  exit 1
fi

if [[ -z "$INPUT" || ! -f "$INPUT" ]]; then
  echo "错误: 必须指定存在的 -i/--input 文件" >&2
  exit 1
fi

PGUSER="${PGUSER:-devault}"
PGDATABASE="${PGDATABASE:-devault}"

restore_local() {
  export PGHOST="${PGHOST:-127.0.0.1}"
  export PGPORT="${PGPORT:-5432}"
  pg_restore -U "$PGUSER" -d "$PGDATABASE" --clean --if-exists --no-owner --no-acl -v "$INPUT"
}

restore_compose() {
  local compose_dir=$1
  local compose_file="$compose_dir/$PROJECT_FILE"
  if [[ ! -f "$compose_file" ]]; then
    echo "错误: 未找到 $compose_file" >&2
    exit 1
  fi
  local tmp_in_container="/tmp/devault-restore-$$.dump"
  (
    cd "$compose_dir"
    if [[ "$RESTART_SERVICES" == "1" ]]; then
      docker compose -f "$PROJECT_FILE" stop api scheduler 2>/dev/null || true
    fi
    docker compose -f "$PROJECT_FILE" cp "$INPUT" "postgres:$tmp_in_container"
    docker compose -f "$PROJECT_FILE" exec -T postgres \
      psql -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 -c \
      "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PGDATABASE}' AND pid <> pg_backend_pid();" \
      >/dev/null
    docker compose -f "$PROJECT_FILE" exec -T postgres \
      pg_restore -U "$PGUSER" -d "$PGDATABASE" --clean --if-exists --no-owner --no-acl -v "$tmp_in_container"
    docker compose -f "$PROJECT_FILE" exec -T postgres rm -f "$tmp_in_container"
    if [[ "$RESTART_SERVICES" == "1" ]]; then
      docker compose -f "$PROJECT_FILE" start api scheduler
    fi
  )
}

if [[ -n "$COMPOSE_DIR" ]]; then
  restore_compose "$COMPOSE_DIR"
else
  restore_local
fi

echo "恢复命令已结束。若应用版本新于备份时的 schema，请在 api 容器或迁移入口执行: alembic upgrade head"
