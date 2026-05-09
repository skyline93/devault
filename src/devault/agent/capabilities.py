"""Agent-side gating for control plane ``server_capabilities`` (Heartbeat / Register)."""

from __future__ import annotations


def gate_multipart_resume(server_capabilities: frozenset[str]) -> bool:
    return "multipart_resume" in server_capabilities


def gate_multipart_upload(server_capabilities: frozenset[str]) -> bool:
    return "multipart_upload" in server_capabilities
