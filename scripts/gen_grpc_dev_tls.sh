#!/usr/bin/env bash
# Generate a dev CA + server cert (for Envoy or direct gRPC TLS) + optional client cert for mTLS demos.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/deploy/tls/dev}"
mkdir -p "$OUT"
cd "$OUT"
if [[ -f ca.key && -f server.crt ]]; then
  echo "Certs already exist in $OUT — remove them to regenerate."
  exit 0
fi
openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 825 -out ca.crt -subj "/CN=DeVault Dev gRPC CA"
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=grpc-gateway"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 825 -sha256
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/CN=devault-agent"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 825 -sha256
rm -f ./*.csr
echo "Generated TLS material under $OUT (keep ca.key private; commit only if this is throwaway dev)."
