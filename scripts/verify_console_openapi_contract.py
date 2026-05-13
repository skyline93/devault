#!/usr/bin/env python3
"""§十四-17 / 十五-19：OpenAPI 契约闸门（无 `/ui`；关键 schema 字段存在）+ 供 `console/` codegen 消费。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _props(schema: dict) -> dict:
    return schema.get("properties") or {}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: verify_console_openapi_contract.py <openapi.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"missing openapi file: {path}", file=sys.stderr)
        return 1
    doc = json.loads(path.read_text(encoding="utf-8"))
    failed = False

    paths = doc.get("paths") or {}
    ui_paths = [p for p in paths if p.startswith("/ui") or p == "/ui"]
    if ui_paths:
        print(f"unexpected /ui routes in OpenAPI (Jinja 已下线): {ui_paths[:20]}", file=sys.stderr)
        failed = True

    if "/api/v1/auth/session" not in paths:
        print("missing path /api/v1/auth/session", file=sys.stderr)
        failed = True

    if "/api/v1/storage-profiles" not in paths:
        print("missing path /api/v1/storage-profiles (storage profiles API)", file=sys.stderr)
        failed = True

    if "/api/v1/jobs" not in paths:
        print("missing path /api/v1/jobs", file=sys.stderr)
        failed = True
    else:
        jget = (paths.get("/api/v1/jobs") or {}).get("get") or {}
        jparams = {p.get("name") for p in (jget.get("parameters") or []) if isinstance(p, dict)}
        for needle in ("kind", "status"):
            if needle not in jparams:
                print(f"GET /api/v1/jobs missing query parameter {needle!r} (十五-23)", file=sys.stderr)
                failed = True

    schemas = (doc.get("components") or {}).get("schemas") or {}
    job = schemas.get("JobOut")
    if not isinstance(job, dict):
        print("missing components.schemas.JobOut", file=sys.stderr)
        failed = True
    else:
        jp = _props(job)
        for needle in (
            "lease_agent_hostname",
            "completed_agent_hostname",
            "config_snapshot",
            "result_meta",
        ):
            if needle not in jp:
                print(f"JobOut.properties missing {needle!r}", file=sys.stderr)
                failed = True

    auth_sess = schemas.get("AuthSessionOut")
    if not isinstance(auth_sess, dict):
        print("missing components.schemas.AuthSessionOut", file=sys.stderr)
        failed = True
    else:
        ap = _props(auth_sess)
        for needle in ("principal_kind", "user_id", "email", "tenants", "needs_mfa"):
            if needle not in ap:
                print(f"AuthSessionOut.properties missing {needle!r} (§十六-06)", file=sys.stderr)
                failed = True

    tenant_out = schemas.get("TenantOut")
    if not isinstance(tenant_out, dict):
        print("missing components.schemas.TenantOut", file=sys.stderr)
        failed = True
    else:
        tp = _props(tenant_out)
        for needle in (
            "require_mfa_for_admins",
            "sso_oidc_issuer",
            "sso_oidc_audience",
            "sso_password_login_disabled",
            "sso_jit_provisioning",
        ):
            if needle not in tp:
                print(f"TenantOut.properties missing {needle!r} (§十六 P2)", file=sys.stderr)
                failed = True

    sess_tenant = schemas.get("SessionTenantRow")
    if not isinstance(sess_tenant, dict):
        print("missing components.schemas.SessionTenantRow", file=sys.stderr)
        failed = True
    else:
        stp = _props(sess_tenant)
        if "sso_password_login_disabled" not in stp:
            print("SessionTenantRow.properties missing 'sso_password_login_disabled' (§十六-12)", file=sys.stderr)
            failed = True

    pol = schemas.get("PolicyOut")
    if not isinstance(pol, dict):
        print("missing components.schemas.PolicyOut", file=sys.stderr)
        failed = True
    else:
        pp = _props(pol)
        for needle in ("bound_agent_id", "updated_at"):
            if needle not in pp:
                print(f"PolicyOut.properties missing {needle!r}", file=sys.stderr)
                failed = True

    art = schemas.get("ArtifactOut")
    if not isinstance(art, dict):
        print("missing components.schemas.ArtifactOut", file=sys.stderr)
        failed = True
    else:
        ap = _props(art)
        if "storage_profile_id" not in ap:
            print("ArtifactOut.properties missing 'storage_profile_id'", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
