"""Control-plane admin CLI (database API keys). Run on a host with DEVAULT_DATABASE_URL."""

from __future__ import annotations

import secrets
import sys
import uuid

import typer
from sqlalchemy import select

from devault import __version__
from devault.db.models import ControlPlaneApiKey, ConsoleUser, Tenant, TenantMembership
from devault.db.session import SessionLocal
from devault.security.passwords import hash_password
from devault.security.token_resolve import hash_api_token

app = typer.Typer(no_args_is_help=True, help="DeVault control-plane admin (database operations)")


@app.command("create-api-key")
def create_api_key(
    name: str = typer.Option(..., "--name", "-n", help="Human-readable label stored in DB"),
    role: str = typer.Option(
        ...,
        "--role",
        "-r",
        help="admin | operator | auditor",
    ),
    tenants: str = typer.Option(
        "",
        "--tenant",
        "-t",
        help="Repeatable or comma-separated tenant UUIDs; omit for all tenants (admin-style)",
    ),
) -> None:
    role_l = role.strip().lower()
    if role_l not in ("admin", "operator", "auditor"):
        typer.echo("role must be admin, operator, or auditor", err=True)
        raise typer.Exit(2)
    raw = secrets.token_urlsafe(32)
    h = hash_api_token(raw)
    tenant_ids: list[uuid.UUID] | None
    parts = [p.strip() for p in tenants.replace(",", " ").split() if p.strip()]
    if parts:
        tenant_ids = [uuid.UUID(x) for x in parts]
    elif role_l == "admin":
        tenant_ids = None
    else:
        typer.echo("operator/auditor keys require at least one --tenant UUID", err=True)
        raise typer.Exit(2)

    allowed: list | None = None if tenant_ids is None else [str(x) for x in tenant_ids]

    db = SessionLocal()
    try:
        row = ControlPlaneApiKey(
            name=name.strip(),
            token_hash=h,
            role=role_l,
            allowed_tenant_ids=allowed,
            enabled=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        typer.echo(f"Created API key id={row.id} name={row.name!r} role={role_l}")
        typer.echo("TOKEN (store securely; shown once):")
        typer.echo(raw)
    finally:
        db.close()


@app.command("create-console-user")
def create_console_user(
    email: str = typer.Option(..., "--email", help="Unique login email (normalized to lower-case)"),
    password: str = typer.Option(..., "--password", help="Plain password (min 12 chars; Argon2id hash stored)"),
    tenant: uuid.UUID = typer.Option(..., "--tenant", help="Tenant UUID to attach membership"),
    role: str = typer.Option(
        "tenant_admin",
        "--role",
        help="tenant_admin | operator | auditor",
    ),
) -> None:
    """§十六-01/05: create a human console user and tenant membership (bootstrap SaaS operators)."""
    role_l = role.strip().lower()
    if role_l not in ("tenant_admin", "operator", "auditor"):
        typer.echo("role must be tenant_admin, operator, or auditor", err=True)
        raise typer.Exit(2)
    email_n = email.strip().lower()
    ph = hash_password(password)
    db = SessionLocal()
    try:
        if db.get(Tenant, tenant) is None:
            typer.echo(f"tenant not found: {tenant}", err=True)
            raise typer.Exit(2)
        existing = db.scalar(select(ConsoleUser).where(ConsoleUser.email == email_n).limit(1))
        if existing is not None:
            typer.echo(f"user already exists: {email_n!r}", err=True)
            raise typer.Exit(2)
        u = ConsoleUser(email=email_n, password_hash=ph, disabled=False)
        db.add(u)
        db.flush()
        db.add(TenantMembership(user_id=u.id, tenant_id=tenant, role=role_l))
        db.commit()
        typer.echo(f"Created console user id={u.id} email={email_n!r} membership role={role_l}")
    finally:
        db.close()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        typer.echo(__version__)
        return
    app()


if __name__ == "__main__":
    main()
