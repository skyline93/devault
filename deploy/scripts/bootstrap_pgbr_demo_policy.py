#!/usr/bin/env python3
"""After demo Agents register, create a demo postgres_pgbackrest policy (optional).

Runs in compose service ``demo-pgbr-policy-init`` (profile ``with-agent``).
Enable with ``DEMO_STACK_PGBR_ENABLED=true`` (set in docker-compose for that service).

Secrets (S3 keys) stay in Agent env only; policy JSON holds non-secret repo fields.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


def _truthy_env(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _json_req(method: str, url: str, *, body: dict | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict | list | str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            code = resp.getcode()
            if not raw:
                return code, {}
            try:
                return code, json.loads(raw)
            except json.JSONDecodeError:
                return code, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def _tenant_headers(bearer: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {bearer}",
        "X-DeVault-Tenant-Id": tenant_id,
    }


def main() -> int:
    if not _truthy_env("DEMO_STACK_PGBR_ENABLED", default=False):
        print("DEMO_STACK_PGBR_ENABLED not set; skipping pgBackRest demo policy bootstrap.", file=sys.stderr)
        return 0

    iam = os.environ.get("DEMO_STACK_IAM_BASE", "http://iam:8100").rstrip("/")
    api = os.environ.get("DEMO_STACK_DEVAULT_API", "http://api:8000").rstrip("/")
    email = os.environ.get("DEMO_STACK_PLATFORM_EMAIL", "demo@devault.com").strip() or "demo@devault.com"
    password = os.environ.get("DEMO_STACK_PLATFORM_PASSWORD", "Devault12345")
    slug = os.environ.get("DEMO_STACK_TENANT_SLUG", "demo").strip().lower()
    policy_name = os.environ.get("DEMO_STACK_PGBR_POLICY_NAME", "demo-pgbackrest").strip() or "demo-pgbackrest"
    min_agents = int(os.environ.get("DEMO_STACK_PGBR_MIN_AGENTS", "1").strip() or "1")
    agent_index = int(os.environ.get("DEMO_STACK_PGBR_AGENT_INDEX", "0").strip() or "0")

    code, login_body = _json_req("POST", f"{iam}/v1/auth/login", body={"email": email, "password": password})
    if code != 200 or not isinstance(login_body, dict) or "access_token" not in login_body:
        print(f"IAM login failed: HTTP {code} {login_body!r}", file=sys.stderr)
        return 1
    bearer = str(login_body["access_token"])
    iam_hdr = {"Authorization": f"Bearer {bearer}"}

    code_l, lst = _json_req("GET", f"{iam}/v1/tenants", headers=iam_hdr)
    if code_l != 200 or not isinstance(lst, list):
        print(f"IAM list tenants failed: HTTP {code_l} {lst!r}", file=sys.stderr)
        return 1
    tid: str | None = None
    for row in lst:
        if isinstance(row, dict) and str(row.get("slug", "")).lower() == slug:
            tid = str(row.get("id") or "")
            break
    if not tid:
        print(f"IAM tenant slug {slug!r} not found.", file=sys.stderr)
        return 1

    th = _tenant_headers(bearer, tid)
    deadline = time.monotonic() + float(os.environ.get("DEMO_STACK_PGBR_AGENT_WAIT_SEC", "180").strip() or "180")
    agents: list[dict] = []
    while time.monotonic() < deadline:
        code_a, body_a = _json_req("GET", f"{api}/api/v1/tenant-agents", headers=th)
        if code_a == 200 and isinstance(body_a, list):
            agents = [x for x in body_a if isinstance(x, dict) and x.get("id")]
            if len(agents) >= min_agents:
                break
        time.sleep(3)
    if len(agents) < min_agents:
        print(f"Timed out waiting for {min_agents} tenant agent(s); saw {len(agents)}.", file=sys.stderr)
        return 1

    agents.sort(key=lambda x: str(x.get("id") or ""))
    if agent_index < 0 or agent_index >= len(agents):
        print(f"DEMO_STACK_PGBR_AGENT_INDEX={agent_index} out of range (agents={len(agents)})", file=sys.stderr)
        return 1
    bound = str(agents[agent_index]["id"])

    code_pol, body_pol = _json_req("GET", f"{api}/api/v1/policies", headers=th)
    if code_pol == 200 and isinstance(body_pol, list):
        for p in body_pol:
            if isinstance(p, dict) and str(p.get("name") or "") == policy_name:
                print(f"Policy {policy_name!r} already exists; skipping create.", file=sys.stderr)
                return 0

    pg_host = os.environ.get("DEMO_PGBR_PG_HOST", "postgres-pgbr-demo").strip()
    pg_port = int(os.environ.get("DEMO_PGBR_PG_PORT", "5432").strip() or "5432")
    pg_data = os.environ.get("DEMO_PGBR_PG_DATA_PATH", "/var/lib/postgresql/data").strip()
    stanza = os.environ.get("DEMO_PGBR_STANZA", "demo").strip() or "demo"
    bucket = os.environ.get("DEVAULT_S3_BUCKET", "devault").strip() or "devault"
    prefix = os.environ.get("DEMO_PGBR_S3_PREFIX", "pgbr-demo/").strip() or "pgbr-demo/"
    region = os.environ.get("DEMO_PGBR_S3_REGION", "us-east-1").strip() or "us-east-1"
    endpoint = os.environ.get("DEMO_PGBR_S3_ENDPOINT", "http://minio:9000").strip() or "http://minio:9000"

    body = {
        "name": policy_name,
        "plugin": "postgres_pgbackrest",
        "enabled": True,
        "bound_agent_id": bound,
        "config": {
            "version": 1,
            "stanza": stanza,
            "pg_host": pg_host,
            "pg_port": pg_port,
            "pg_data_path": pg_data,
            "pgbackrest_operation": "backup",
            "backup_type": "full",
            "repo_s3_bucket": bucket,
            "repo_s3_prefix": prefix,
            "repo_s3_region": region,
            "repo_s3_endpoint": endpoint,
        },
    }
    code_c, body_c = _json_req("POST", f"{api}/api/v1/policies", body=body, headers=th)
    if code_c in (200, 201):
        print(f"Created demo policy {policy_name!r} bound to agent {bound}.", file=sys.stderr)
        return 0
    print(f"POST /api/v1/policies failed: HTTP {code_c} {body_c!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
