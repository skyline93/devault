#!/bin/sh
# Used by deploy/docker-compose.yml for the demo agent: prefer DEVAULT_AGENT_TOKEN from the
# environment; otherwise read the one-line secret written by bootstrap_demo_stack.py.
set -e
if [ -n "${DEVAULT_AGENT_TOKEN:-}" ]; then
  exec devault-agent "$@"
fi
if [ ! -s /shared/demo-agent-token ]; then
  echo "Missing DEVAULT_AGENT_TOKEN and empty /shared/demo-agent-token (run demo-stack-init or set DEVAULT_AGENT_TOKEN)." >&2
  exit 1
fi
export DEVAULT_AGENT_TOKEN=$(tr -d '\n\r' < /shared/demo-agent-token)
exec devault-agent "$@"
