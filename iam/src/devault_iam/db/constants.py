"""IAM database naming: physical tables are ``{TABLE_PREFIX}_{logical}``."""

from __future__ import annotations

TABLE_PREFIX = "iam"


def prefixed_table(logical_name: str) -> str:
    return f"{TABLE_PREFIX}_{logical_name}"


def prefixed_fk(logical_table: str, column: str) -> str:
    return f"{prefixed_table(logical_table)}.{column}"
