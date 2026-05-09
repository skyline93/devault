# DeVault

Enterprise-oriented **backup and restore** platform: a control plane (HTTP API, gRPC, PostgreSQL, Redis) and edge **Agents** (gRPC + S3-compatible storage), **pull**-based scheduling, policies and Cron, cancel/retry, Prometheus metrics, and a lightweight Web UI.

> **中文说明**见 [`README.zh-CN.md`](README.zh-CN.md)。

## Quick start

From the repository root:

```bash
cd deploy
docker compose up --build -d
```

Then open **Swagger** at <http://127.0.0.1:8000/docs>. In Compose, database migrations run on **api** startup (`alembic upgrade head`).

## Documentation

- **Full user and ops guides**: [documentation site source](website/), content in [`website/docs/`](website/docs/index.md). Local preview: `cd website && npm ci && npm start` → <http://localhost:3000>
- **Control plane ↔ Agent compatibility matrix** (machine-readable): [`docs/compatibility.json`](docs/compatibility.json)
- **Release notes**: [`docs/RELEASE.md`](docs/RELEASE.md)

API surfaces, gRPC/TLS, S3, and Helm are covered in the doc site; this root README stays short.

## Repository layout

| Path | Purpose |
|------|---------|
| `src/devault/` | Control plane and Agent Python packages |
| `deploy/` | Docker Compose, images, and Helm chart |
| `website/` | Docusaurus documentation site |
| `tests/` | pytest suite |

## Local development (summary)

You need **Python ≥ 3.12**, PostgreSQL, Redis, and an S3-compatible endpoint (aligned with production Agent presigning). See the doc site for install/run examples; common commands:

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
pytest -q
```

After changing `proto/agent.proto`, run `bash scripts/gen_proto.sh` (requires `grpcio-tools`).

## License

MIT (add a root `LICENSE` file if you want an explicit copy in-repo).
