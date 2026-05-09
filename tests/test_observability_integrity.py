from __future__ import annotations

from devault.observability.metrics import agent_error_class


def test_agent_error_class_integrity_codes() -> None:
    assert agent_error_class("CHECKSUM_MISMATCH") == "integrity"
    assert agent_error_class("invalid_manifest") == "integrity"
    assert agent_error_class(None) == "operational"
    assert agent_error_class("") == "operational"


def test_agent_error_class_operational_default() -> None:
    assert agent_error_class("STORAGE_ERROR") == "operational"
    assert agent_error_class("FAILED") == "operational"
