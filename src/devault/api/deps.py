from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from devault.db.session import SessionLocal
from devault.settings import get_settings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_bearer(authorization: str | None = Header(None)) -> None:
    settings = get_settings()
    if not settings.api_token:
        return
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.api_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


AuthDep = Depends(verify_bearer)
