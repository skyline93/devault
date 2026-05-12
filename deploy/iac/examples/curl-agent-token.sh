#!/usr/bin/env bash
# Example: create a tenant Agent token (requires IAM Bearer + X-DeVault-Tenant-Id).
# Usage:
#   export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
#   export DEVAULT_TENANT_ID=<tenant-uuid>
#   export DEVAULT_IAM_BEARER=<access-jwt>
set -euo pipefail

: "${DEVAULT_API_BASE_URL:?}"
: "${DEVAULT_TENANT_ID:?}"
: "${DEVAULT_IAM_BEARER:?}"

curl -sfS -X POST "${DEVAULT_API_BASE_URL}/api/v1/agent-tokens" \
  -H "Authorization: Bearer ${DEVAULT_IAM_BEARER}" \
  -H "X-DeVault-Tenant-Id: ${DEVAULT_TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"label":"demo-edge","description":"IaC example token"}'
