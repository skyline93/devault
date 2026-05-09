#!/usr/bin/env bash
# Starts TLS Envoy + three api replicas using grpc-ha-example overlay (no host ports on api).
# Prereq: bash scripts/gen_grpc_dev_tls.sh from repo root (deploy/tls/dev/).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEPLOY="$ROOT/deploy"
TLS_CERT="$DEPLOY/tls/dev/server.crt"

if [[ ! -f "$TLS_CERT" ]]; then
  echo "Missing $TLS_CERT — run from repo root: bash scripts/gen_grpc_dev_tls.sh" >&2
  exit 1
fi

cd "$DEPLOY"
docker compose \
  -f docker-compose.yml \
  -f docker-compose.grpc-tls.yml \
  -f docker-compose.grpc-ha-example.yml \
  up --build -d --scale api=3

docker compose \
  -f docker-compose.yml \
  -f docker-compose.grpc-tls.yml \
  -f docker-compose.grpc-ha-example.yml \
  ps

echo ""
echo "api scaled to 3 replicas (no localhost:8000 on host). Example health check inside one api:"
echo "  cd deploy && docker compose -f docker-compose.yml -f docker-compose.grpc-tls.yml -f docker-compose.grpc-ha-example.yml exec api curl -sS http://127.0.0.1:8000/healthz"
