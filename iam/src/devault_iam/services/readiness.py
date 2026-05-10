from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def database_ready(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
