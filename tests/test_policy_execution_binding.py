"""Policy execution binding schema."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from devault.api.schemas import PolicyCreate


def test_policy_create_requires_bound_agent() -> None:
    with pytest.raises(ValidationError):
        PolicyCreate(
            name="p",
            plugin="file",
            config={
                "version": 1,
                "paths": ["/tmp"],
                "excludes": [],
            },
        )


def test_policy_create_with_bound_agent() -> None:
    aid = uuid.uuid4()
    p = PolicyCreate(
        name="p",
        plugin="file",
        config={"version": 1, "paths": ["/tmp"], "excludes": []},
        bound_agent_id=aid,
    )
    assert p.bound_agent_id == aid
