#!/usr/bin/env bash
# Example: PUT agent enrollment (admin). Usage:
#   export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
#   export DEVAULT_API_TOKEN=changeme
#   export DEVAULT_AGENT_ID=00000000-0000-4000-8000-000000000001
#   export DEVAULT_TENANT_ID=<tenant-uuid>
set -euo pipefail
: "${DEVAULT_API_BASE_URL:?}"
: "${DEVAULT_API_TOKEN:?}"
: "${DEVAULT_AGENT_ID:?}"
: "${DEVAULT_TENANT_ID:?}"
curl -sfS -X PUT "${DEVAULT_API_BASE_URL}/api/v1/agents/${DEVAULT_AGENT_ID}/enrollment" \
  -H "Authorization: Bearer ${DEVAULT_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"allowed_tenant_ids\":[\"${DEVAULT_TENANT_ID}\"]}"
