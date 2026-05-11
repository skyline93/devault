#!/usr/bin/env python3
"""Mirror an IAM tenant into DeVault (UUID + slug) after stacks are up.

Typical use (Docker Compose, **profile** ``with-console`` — e.g. ``make demo-stack-up``):

1. IAM runs ``iam-admin bootstrap create-platform-user`` when ``IAM_DEMO_AUTO_BOOTSTRAP`` is true (Compose default).
2. ``demo-stack-init`` runs with default platform email/password (same as IAM); override with ``DEMO_STACK_PLATFORM_*``.
3. ``console`` starts after ``demo-stack-init`` exits successfully.

Standalone: ``docker compose --profile with-console up demo-stack-init`` (or set env and run this script).

Environment (defaults suit in-network Compose service names):

- ``DEMO_STACK_IAM_BASE`` — IAM HTTP root (default ``http://iam:8100``).
- ``DEMO_STACK_DEVAULT_API`` — DeVault API root (default ``http://api:8000``).
- ``DEMO_STACK_PLATFORM_EMAIL`` / ``DEMO_STACK_PLATFORM_PASSWORD`` — platform user (defaults match Compose / IAM demo bootstrap).
- ``DEMO_STACK_TENANT_SLUG`` — default ``demo``.
- ``DEMO_STACK_TENANT_NAME`` — default ``Demo``.

Idempotent: if IAM or DeVault already has the slug, exits 0 after ensuring DeVault row exists when possible.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


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


def main() -> int:
    iam = os.environ.get("DEMO_STACK_IAM_BASE", "http://iam:8100").rstrip("/")
    api = os.environ.get("DEMO_STACK_DEVAULT_API", "http://api:8000").rstrip("/")
    email = (
        os.environ.get("DEMO_STACK_PLATFORM_EMAIL", "demo@devault.com").strip()
        or "demo@devault.com"
    )
    password = os.environ.get("DEMO_STACK_PLATFORM_PASSWORD", "Devault12345")
    slug = os.environ.get("DEMO_STACK_TENANT_SLUG", "demo").strip().lower()
    name = os.environ.get("DEMO_STACK_TENANT_NAME", "Demo").strip()

    code, login_body = _json_req(
        "POST",
        f"{iam}/v1/auth/login",
        body={"email": email, "password": password},
    )
    if code != 200:
        print(f"IAM login failed: HTTP {code} {login_body!r}", file=sys.stderr)
        return 1
    if not isinstance(login_body, dict) or "access_token" not in login_body:
        print(f"IAM login unexpected body: {login_body!r}", file=sys.stderr)
        return 1
    bearer = str(login_body["access_token"])

    def iam_headers() -> dict[str, str]:
        return {"Authorization": f"Bearer {bearer}"}

    code_t, t_body = _json_req(
        "POST",
        f"{iam}/v1/tenants",
        body={"name": name, "slug": slug},
        headers=iam_headers(),
    )
    tid: str | None = None
    if code_t == 201 and isinstance(t_body, dict):
        tid = str(t_body.get("id") or "")
    elif code_t == 409:
        code_l, lst = _json_req("GET", f"{iam}/v1/tenants", headers=iam_headers())
        if code_l == 200 and isinstance(lst, list):
            for row in lst:
                if isinstance(row, dict) and str(row.get("slug", "")).lower() == slug:
                    tid = str(row.get("id") or "")
                    break
    else:
        print(f"IAM create tenant failed: HTTP {code_t} {t_body!r}", file=sys.stderr)
        return 1

    if not tid:
        print("Could not resolve IAM tenant id after create/list.", file=sys.stderr)
        return 1

    code_d, d_body = _json_req(
        "POST",
        f"{api}/api/v1/tenants",
        body={"id": tid, "name": name, "slug": slug},
        headers=iam_headers(),
    )
    if code_d in (200, 201):
        print(f"DeVault tenant upsert ok: {slug} ({tid})", file=sys.stderr)
        return 0
    if code_d == 409:
        print(f"DeVault tenant slug already exists ({slug}); treating as success.", file=sys.stderr)
        return 0

    print(f"DeVault POST /api/v1/tenants failed: HTTP {code_d} {d_body!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
