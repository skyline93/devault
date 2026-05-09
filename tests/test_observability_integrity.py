from __future__ import annotations

from pathlib import Path

from devault.observability.metrics import agent_error_class


def test_prometheus_alert_rules_file_contains_expected_groups() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "deploy/prometheus/alerts.yml").read_text(encoding="utf-8")
    assert "devault-backup-integrity" in text
    assert "devault-operations" in text
    assert "DeVaultPolicyLockContentionBurst" in text


def test_agent_error_class_integrity_codes() -> None:
    assert agent_error_class("CHECKSUM_MISMATCH") == "integrity"
    assert agent_error_class("invalid_manifest") == "integrity"
    assert agent_error_class(None) == "operational"
    assert agent_error_class("") == "operational"


def test_agent_error_class_operational_default() -> None:
    assert agent_error_class("STORAGE_ERROR") == "operational"
    assert agent_error_class("FAILED") == "operational"
