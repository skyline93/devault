#!/bin/sh
# One-shot (compose): create pgBackRest stanza on MinIO for the demo target PostgreSQL.
# Requires pgbackrest package in image and PGBACKREST_REPO1_S3_* in environment.
set -eu

STANZA="${DEMO_PGBR_STANZA:-demo}"
PG_HOST="${DEMO_PGBR_PG_HOST:-postgres-pgbr-demo}"
PG_PORT="${DEMO_PGBR_PG_PORT:-5432}"
PG_DATA="${DEMO_PGBR_PG_DATA_PATH:-/var/lib/postgresql/data}"
BUCKET="${DEVAULT_S3_BUCKET:-devault}"
PREFIX="${DEMO_PGBR_S3_PREFIX:-pgbr-demo/}"
ENDPOINT="${DEMO_PGBR_S3_ENDPOINT:-http://minio:9000}"
REGION="${DEMO_PGBR_S3_REGION:-us-east-1}"

CONF_DIR="${TMPDIR:-/tmp}/devault-pgbr-stanza-init-$$"
mkdir -p "$CONF_DIR"
LOG_DIR="$CONF_DIR/pgbr-logs"
mkdir -p "$LOG_DIR"
CONF="$CONF_DIR/pgbackrest.conf"
trap 'rm -rf "$CONF_DIR"' EXIT

# repo1-path = prefix inside S3 bucket (pgBackRest 2.55+; repo1-s3-path-prefix is invalid).
PREFIX_TRIM="${PREFIX#/}"
PREFIX_TRIM="${PREFIX_TRIM%/}"
if [ -z "$PREFIX_TRIM" ]; then
  REPO1_PATH="/"
else
  REPO1_PATH="/${PREFIX_TRIM}"
fi

echo "Waiting for TCP ${PG_HOST}:${PG_PORT}..." >&2
python3 - <<PY
import os, socket, time
h = os.environ.get("DEMO_PGBR_PG_HOST", "postgres-pgbr-demo")
p = int(os.environ.get("DEMO_PGBR_PG_PORT", "5432"))
for i in range(120):
    try:
        s = socket.create_connection((h, p), timeout=2)
        s.close()
        print("postgres reachable", flush=True)
        break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("timeout waiting for postgres-pgbr-demo")
PY

cat >"$CONF" <<EOF
[global]
log-path=${LOG_DIR}
repo1-type=s3
repo1-s3-bucket=${BUCKET}
repo1-path=${REPO1_PATH}
repo1-s3-region=${REGION}
repo1-s3-endpoint=${ENDPOINT}
repo1-storage-verify-tls=n

[${STANZA}]
pg1-host=${PG_HOST}
pg1-port=${PG_PORT}
pg1-path=${PG_DATA}
EOF

echo "Running pgbackrest stanza-create (idempotent if repo already has stanza)..." >&2
set +e
pgbackrest --config="$CONF" --stanza="$STANZA" stanza-create
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  echo "stanza-create exit=$rc (continuing if stanza already exists)" >&2
fi
pgbackrest --config="$CONF" --stanza="$STANZA" check
echo "pgBackRest stanza ${STANZA} ok." >&2
