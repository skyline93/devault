from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

from devault.db.constants import TABLE_PREFIX, prefixed_table


class Base(DeclarativeBase):
    """Declarative base: set logical ``__tablename__`` only; physical name is ``{TABLE_PREFIX}_{logical}``."""

    def __init_subclass__(cls, **kwargs) -> None:
        if "__abstract__" in cls.__dict__ and cls.__dict__["__abstract__"]:
            super().__init_subclass__(**kwargs)
            return
        if "__tablename__" in cls.__dict__:
            logical = cls.__dict__["__tablename__"]
            if isinstance(logical, str) and not logical.startswith(f"{TABLE_PREFIX}_"):
                type.__setattr__(cls, "__tablename__", prefixed_table(logical))
        super().__init_subclass__(**kwargs)
