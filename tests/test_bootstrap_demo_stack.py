"""deploy/scripts/bootstrap_demo_stack.py — demo Agent token file (HTTP mocked)."""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "bootstrap_demo_stack",
    _ROOT / "deploy/scripts/bootstrap_demo_stack.py",
)
assert _SPEC and _SPEC.loader
b = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(b)


def test_ensure_demo_agent_token_file_creates_on_empty_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    token_file = tmp_path / "secret"
    monkeypatch.setenv("DEMO_STACK_AGENT_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("DEMO_STACK_AGENT_TOKEN_LABEL", "demo-stack-agent")
    monkeypatch.delenv("DEMO_STACK_SKIP_AGENT_TOKEN_BOOTSTRAP", raising=False)

    calls: list[tuple[str, str]] = []

    def fake_json_req(
        method: str,
        url: str,
        *,
        body: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict | list | str]:
        calls.append((method, url))
        assert headers is not None
        assert headers.get("X-DeVault-Tenant-Id") == tid
        if method == "GET" and url.endswith("/api/v1/agent-tokens"):
            return 200, []
        if method == "POST" and url.endswith("/api/v1/agent-tokens"):
            assert body is not None
            assert body.get("label") == "demo-stack-agent"
            return 201, {"plaintext_secret": "plain-one"}
        raise AssertionError((method, url))

    monkeypatch.setattr(b, "_json_req", fake_json_req)

    tid = str(uuid.uuid4())
    assert b._ensure_demo_agent_token_file(api="http://api", bearer="tok", tenant_id=tid) == 0
    assert token_file.read_text(encoding="utf-8").strip() == "plain-one"
    assert [c[0] for c in calls] == ["GET", "POST"]


def test_ensure_demo_agent_token_file_skips_when_nonempty_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token_file = tmp_path / "secret"
    token_file.write_text("cached\n", encoding="utf-8")
    monkeypatch.setenv("DEMO_STACK_AGENT_TOKEN_FILE", str(token_file))

    def boom(*_a: object, **_k: object) -> tuple[int, dict]:
        raise AssertionError("should not call HTTP when token file is populated")

    monkeypatch.setattr(b, "_json_req", boom)
    assert b._ensure_demo_agent_token_file(api="http://api", bearer="b", tenant_id=str(uuid.uuid4())) == 0


def test_ensure_demo_agent_token_file_errors_when_label_exists_but_file_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token_file = tmp_path / "secret"
    token_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("DEMO_STACK_AGENT_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("DEMO_STACK_AGENT_TOKEN_LABEL", "demo-stack-agent")

    def fake_json_req(method: str, url: str, **_k: object) -> tuple[int, list]:
        if method == "GET":
            return 200, [{"label": "demo-stack-agent", "id": str(uuid.uuid4())}]
        raise AssertionError

    monkeypatch.setattr(b, "_json_req", fake_json_req)
    assert b._ensure_demo_agent_token_file(api="http://api", bearer="b", tenant_id=str(uuid.uuid4())) == 1
