"""Operational CLI: ``iam-admin bootstrap …`` (no HTTP server)."""

from __future__ import annotations

import argparse
import sys
from getpass import getpass
from pathlib import Path

from sqlalchemy import func, select

from devault_iam.db.models import User
from devault_iam.db.session import SessionLocal, reset_engine_for_tests
from devault_iam.services.audit_service import mask_email, record_audit_event
from devault_iam.security.passwords import hash_password
from devault_iam.settings import clear_settings_cache, get_settings


def _bootstrap_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="iam-admin", description="DeVault IAM administration CLI")
    sub = root.add_subparsers(dest="cmd", required=True)
    boot = sub.add_parser("bootstrap", help="First-time platform operator setup")
    bsub = boot.add_subparsers(dest="boot_cmd", required=True)

    create = bsub.add_parser(
        "create-platform-user",
        help="Create the first (and only via this path) platform admin if none exists",
    )
    create.add_argument("--email", required=True, help="Login email (normalized to lower case)")
    create.add_argument(
        "--password-file",
        metavar="PATH",
        help="Read initial password from file (first line only); if omitted, prompt on TTY",
    )
    create.add_argument("--name", default="", help="Display name (default: local part of email)")

    bsub.add_parser("status", help="Show whether a platform admin user exists")

    return root


def _read_password_from_file(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    line = raw.splitlines()[0] if raw.splitlines() else ""
    return line.strip()


def run_bootstrap_create(*, email: str, password: str, name: str) -> int:
    """Return process exit code (0 = success)."""
    email_n = email.strip().lower()
    if not email_n or "@" not in email_n:
        print("error: invalid --email", file=sys.stderr)
        return 2
    if not password:
        print("error: empty password", file=sys.stderr)
        return 2

    clear_settings_cache()
    reset_engine_for_tests()
    get_settings()

    db = SessionLocal()
    try:
        existing_admin = db.scalar(select(User.id).where(User.is_platform_admin.is_(True)))
        if existing_admin is not None:
            print("error: a platform admin user already exists (bootstrap is idempotent).", file=sys.stderr)
            record_audit_event(
                action="platform.bootstrap",
                outcome="failure",
                detail="platform_admin_already_exists",
                context={"email_masked": mask_email(email_n)},
            )
            return 1

        if db.scalar(select(User.id).where(User.email == email_n)) is not None:
            print("error: email already registered; choose a fresh email for bootstrap.", file=sys.stderr)
            record_audit_event(
                action="platform.bootstrap",
                outcome="failure",
                detail="email_taken",
                context={"email_masked": mask_email(email_n)},
            )
            return 1

        display = (name or "").strip() or email_n.split("@", 1)[0]
        user = User(
            email=email_n,
            password_hash=hash_password(password),
            name=display,
            status="active",
            is_platform_admin=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        record_audit_event(
            action="platform.bootstrap",
            outcome="success",
            actor_user_id=user.id,
            detail="platform_user_created",
            context={"email_masked": mask_email(email_n)},
        )
        print(f"ok: created platform admin user id={user.id} email={email_n!r}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_bootstrap_status() -> int:
    clear_settings_cache()
    reset_engine_for_tests()
    get_settings()
    db = SessionLocal()
    try:
        n_admins = int(
            db.scalar(select(func.count()).select_from(User).where(User.is_platform_admin.is_(True))) or 0
        )
        n_users = int(db.scalar(select(func.count()).select_from(User)) or 0)
        print(f"platform_admin_users: {n_admins}")
        print(f"total_users: {n_users}")
        return 0
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = _bootstrap_parser().parse_args(argv)
    if args.cmd != "bootstrap":
        return 2
    if args.boot_cmd == "status":
        return run_bootstrap_status()
    if args.boot_cmd == "create-platform-user":
        pw: str
        if args.password_file:
            pw = _read_password_from_file(Path(args.password_file))
        else:
            if not sys.stdin.isatty():
                print("error: no TTY for password prompt; use --password-file", file=sys.stderr)
                return 2
            pw = getpass("Initial password: ")
            pw2 = getpass("Confirm password: ")
            if pw != pw2:
                print("error: passwords do not match", file=sys.stderr)
                return 2
        return run_bootstrap_create(email=args.email, password=pw, name=args.name)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
