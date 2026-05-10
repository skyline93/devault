"""Policy execution binding schema (§十四)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from devault.api.schemas import PolicyCreate


def test_policy_create_binding_mutually_exclusive() -> None:
    with pytest.raises(ValidationError):
        PolicyCreate(
            name="p",
            plugin="file",
            config={
                "version": 1,
                "paths": ["/tmp"],
                "excludes": [],
            },
            bound_agent_id=uuid.uuid4(),
            bound_agent_pool_id=uuid.uuid4(),
        )


def test_policy_create_binding_optional() -> None:
    p = PolicyCreate(
        name="p",
        plugin="file",
        config={"version": 1, "paths": ["/tmp"], "excludes": []},
    )
    assert p.bound_agent_id is None and p.bound_agent_pool_id is None
