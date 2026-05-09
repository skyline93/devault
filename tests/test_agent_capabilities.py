from __future__ import annotations

from devault.agent.capabilities import gate_multipart_resume, gate_multipart_upload


def test_gate_multipart_resume() -> None:
    assert gate_multipart_resume(frozenset(["multipart_resume", "multipart_upload"]))
    assert not gate_multipart_resume(frozenset(["multipart_upload"]))
    assert not gate_multipart_resume(frozenset())


def test_gate_multipart_upload() -> None:
    assert gate_multipart_upload(frozenset(["multipart_upload"]))
    assert not gate_multipart_upload(frozenset(["multipart_resume"]))
    assert not gate_multipart_upload(frozenset())
