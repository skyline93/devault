#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/src/devault/grpc_gen"
mkdir -p "$OUT"
python3 -m grpc_tools.protoc \
  -I "$ROOT/proto" \
  --python_out="$OUT" \
  --grpc_python_out="$OUT" \
  "$ROOT/proto/agent.proto"
# Package-relative import (grpc_tools may emit `import agent_pb2` or `import agent_pb2 as agent__pb2`)
for pat in \
  's/^import agent_pb2$/from . import agent_pb2/' \
  's/^import agent_pb2 as agent__pb2$/from . import agent_pb2 as agent__pb2/'; do
  sed -i.bak "$pat" "$OUT/agent_pb2_grpc.py" 2>/dev/null || sed -i '' "$pat" "$OUT/agent_pb2_grpc.py"
done
rm -f "$OUT/agent_pb2_grpc.py.bak"
echo "Regenerated gRPC stubs in $OUT (remove GRPC_GENERATED_VERSION block in agent_pb2_grpc.py if present)."
