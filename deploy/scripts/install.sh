#!/bin/sh
# DeVault — install from https://github.com/skyline93/devault
#
# One-liner (installs into the current directory; pulls pre-built images from Docker Hub by default):
#   curl -fsSL https://raw.githubusercontent.com/skyline93/devault/main/deploy/scripts/install.sh | sh
#
# Optional flags:
#   --dir PATH   Install directory (default: current directory). Ignored when run from a local checkout.
#   --help
#
# Optional environment (only when you need to deviate from defaults):
#   DEVAULT_REF                 Git branch or tag for compose/script source (default: main).
#   DEVAULT_INSTALL_DIR         Same as --dir if set before the script runs.
#   DEVAULT_IMAGE               Full image ref (default: glf9832/devault:latest-<amd64|arm64> from uname).
#   DEVAULT_INSTALL_BASE_URL    Raw URL of deploy/ on a mirror (default: raw.githubusercontent.com/skyline93/devault/.../deploy).
#
# Local checkout:
#   ./deploy/scripts/install.sh

set -eu

INSTALL_DIR="${DEVAULT_INSTALL_DIR:-${PWD}}"
DIR_FLAG=0
POS_BASE=""

usage() {
  echo "Usage: curl -fsSL https://raw.githubusercontent.com/skyline93/devault/main/deploy/scripts/install.sh | sh"
  echo "       ./deploy/scripts/install.sh"
  echo "Flags: --dir PATH | --help"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -d | --dir)
      DIR_FLAG=1
      INSTALL_DIR="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    http://* | https://*)
      POS_BASE="$1"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing command: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd docker

if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker compose"
elif docker-compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker-compose"
else
  echo "Docker Compose v2 (docker compose) or docker-compose is required." >&2
  exit 1
fi

COMPOSE_FILE="docker-compose.yml"

normalize_base() {
  _b="$1"
  echo "$_b" | sed 's|/*$||'
}

official_raw_deploy() {
  _ref="${DEVAULT_REF:-main}"
  printf "https://raw.githubusercontent.com/skyline93/devault/%s/deploy" "$_ref"
}

resolve_deploy_base() {
  if [ -n "${DEVAULT_INSTALL_BASE_URL:-}" ]; then
    normalize_base "$DEVAULT_INSTALL_BASE_URL"
    return
  fi
  if [ -n "$POS_BASE" ]; then
    normalize_base "$POS_BASE"
    return
  fi
  script_path="$0"
  case "$script_path" in
    */install.sh | install.sh)
      script_dir=$(CDPATH= cd "$(dirname "$script_path")" && pwd)
      normalize_base "$(CDPATH= cd "$script_dir/.." && pwd)"
      return
      ;;
  esac
  official_raw_deploy
}

detect_arch_suffix() {
  _m=$(uname -m)
  case "$_m" in
    x86_64 | amd64) printf amd64 ;;
    aarch64 | arm64) printf arm64 ;;
    *)
      echo "Unsupported machine: $_m (expected x86_64/amd64 or aarch64/arm64)." >&2
      exit 1
      ;;
  esac
}

env_set_devault_image() {
  _val="$1"
  tmp="$(mktemp)"
  if [ -f .env ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        DEVAULT_IMAGE=*) ;;
        *) echo "$line" ;;
      esac
    done < .env > "$tmp"
    mv "$tmp" .env
  else
    : > .env
  fi
  echo "DEVAULT_IMAGE=${_val}" >> .env
}

is_remote_base() {
  case "$1" in
    http://* | https://*) return 0 ;;
    *) return 1 ;;
  esac
}

deploy_base=$(resolve_deploy_base)

if is_remote_base "$deploy_base"; then
  remote=1
else
  remote=0
fi

if [ "$remote" -eq 1 ]; then
  mkdir -p "$INSTALL_DIR"
  cd "$INSTALL_DIR"
  echo ">> Install directory: $(pwd)"
  echo ">> Source: ${deploy_base}"
  echo ">> Fetching ${COMPOSE_FILE}"
  curl -fsSL "${deploy_base}/${COMPOSE_FILE}" -o "$COMPOSE_FILE"
else
  if [ "$DIR_FLAG" -eq 1 ]; then
    echo "Note: --dir is ignored for local checkout; using ${deploy_base}" >&2
  fi
  cd "$deploy_base"
  echo ">> Using checkout deploy directory: $(pwd)"
fi

mkdir -p demo_data/sample
if [ ! -f demo_data/sample/hello.txt ]; then
  printf '%s\n' "DeVault demo file — safe to delete." > demo_data/sample/hello.txt
fi

if [ "$remote" -eq 1 ]; then
  if [ -n "${DEVAULT_IMAGE:-}" ]; then
    img="$DEVAULT_IMAGE"
  else
    _sfx=$(detect_arch_suffix)
    img="glf9832/devault:latest-${_sfx}"
  fi
  env_set_devault_image "$img"
  export DEVAULT_IMAGE="$img"
  echo ">> Using image: $DEVAULT_IMAGE"
elif [ -n "${DEVAULT_IMAGE:-}" ]; then
  export DEVAULT_IMAGE="$DEVAULT_IMAGE"
  echo ">> Using image: $DEVAULT_IMAGE"
fi

echo ">> Pulling images..."
if $DOCKER_COMPOSE -f "$COMPOSE_FILE" pull --help 2>&1 | grep -q -- '--policy'; then
  # shellcheck disable=SC2086
  $DOCKER_COMPOSE -f "$COMPOSE_FILE" pull --policy missing || true
else
  # shellcheck disable=SC2086
  $DOCKER_COMPOSE -f "$COMPOSE_FILE" pull || true
fi

echo ">> Starting stack..."
# shellcheck disable=SC2086
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d

echo ""
echo "DeVault is up. Swagger: http://127.0.0.1:8000/docs"
echo "Stop: cd \"$(pwd)\" && $DOCKER_COMPOSE -f \"$COMPOSE_FILE\" down"
