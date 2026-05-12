#!/bin/sh
# Used by deploy/docker-compose.yml for demo agents: prefer DEVAULT_AGENT_TOKEN from the
# environment; otherwise read the one-line secret written by bootstrap_demo_stack.py.
set -e
TOKEN_FILE="${DEVAULT_AGENT_TOKEN_FILE:-/shared/demo-agent-token}"
if [ -n "${DEVAULT_AGENT_TOKEN:-}" ]; then
  exec devault-agent "$@"
fi
if [ ! -s "$TOKEN_FILE" ]; then
  echo "Missing DEVAULT_AGENT_TOKEN and empty ${TOKEN_FILE} (run demo-stack-init or set DEVAULT_AGENT_TOKEN)." >&2
  exit 1
fi
export DEVAULT_AGENT_TOKEN=$(tr -d '\n\r' < "$TOKEN_FILE")
exec devault-agent "$@"
