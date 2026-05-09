# DeVault

Enterprise-oriented **backup and restore** platform: a control plane (HTTP API, gRPC, PostgreSQL, Redis) and edge **Agents** (gRPC + S3-compatible storage), **pull**-based scheduling, policies and Cron, cancel/retry, Prometheus metrics, and a lightweight Web UI.

> **中文说明**见 [`README.zh-CN.md`](README.zh-CN.md)。

## Quick start

From the repository root:

```bash
cd deploy
docker compose pull && docker compose up -d
```

Then open **Swagger** at <http://127.0.0.1:8000/docs>. In Compose, database migrations run on **api** startup (`alembic upgrade head`).

`docker-compose.yml` uses **pre-built images only** (`image: ${DEVAULT_IMAGE:-glf9832/devault:latest}` for api, scheduler, and agent). Override **`DEVAULT_IMAGE`** for another registry or tag. Build the image separately (`make docker-build-push`, CI, etc.); Compose does not run `build`.

### Remote install (no `git clone`)

Official repo: **[skyline93/devault](https://github.com/skyline93/devault)**. The installer pulls `docker-compose.yml` from the matching raw path and starts the stack in the **current directory** (use `--dir` to change). By default it pulls **Docker Hub** `glf9832/devault:latest-<amd64|arm64>` (from `uname -m`). Set **`DEVAULT_IMAGE`** only if you need a different image ref.

```bash
curl -fsSL https://raw.githubusercontent.com/skyline93/devault/main/deploy/scripts/install.sh | sh
```

Optional: `DEVAULT_REF` (branch or tag, default `main`) to pin which revision of `deploy/` is fetched; `DEVAULT_INSTALL_BASE_URL` only if you mirror the `deploy/` tree elsewhere.

From a **local clone**, `./deploy/scripts/install.sh` runs inside `deploy/`, pulls images, then **`docker compose up -d`**. `--dir` is ignored in that mode.

Maintainers: GitHub Actions secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` (typically the Docker Hub user that owns `glf9832/devault`), optional repository variable `DOCKERHUB_IMAGE` to push under a different repo name. Workflow: `.github/workflows/docker-publish.yml` (default push target: `glf9832/devault`).

**Local build / push (no CI):** from the repo root, `make help` lists image targets. Same `deploy/Dockerfile` as CI, for example:

```bash
make docker-build-push
make docker-buildx-push IMAGE=glf9832/devault:latest
```

(`docker login` to your registry first.) Optional: `PLATFORMS=linux/arm64` for a single-arch buildx `--load` build; override `PLATFORMS_MULTI` for `docker-buildx-push`.

## Documentation

- **Full user and ops guides**: [documentation site source](website/), content in [`website/docs/`](website/docs/index.md). Local preview: `cd website && npm ci && npm start` → <http://localhost:3000>
- **Control plane ↔ Agent compatibility matrix** (machine-readable): [`docs/compatibility.json`](docs/compatibility.json)
- **Release notes**: [`docs/RELEASE.md`](docs/RELEASE.md)

API surfaces, gRPC/TLS, S3, and Helm are covered in the doc site; this root README stays short.

## Repository layout

| Path | Purpose |
|------|---------|
| `Makefile` | Local `docker build` / `push` helpers (`make help`) |
| `src/devault/` | Control plane and Agent Python packages |
| `deploy/` | `docker-compose.yml`, `scripts/install.sh`, images, Helm chart, `demo_data/` sample for the agent bind mount |
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
