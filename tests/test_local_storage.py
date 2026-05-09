from __future__ import annotations

import hashlib
from pathlib import Path

from devault.storage.local import LocalStorage


def test_local_put_get_roundtrip(tmp_path: Path) -> None:
    root = tmp_path / "root"
    st = LocalStorage(root)
    src = tmp_path / "a.bin"
    src.write_bytes(b"hello-devault")
    key = "devault/dev/artifacts/2026/05/07/test/bundle.tar.gz"
    st.put_file(key, src)
    assert st.exists(key)

    out = tmp_path / "out.bin"
    st.get_file(key, out)
    assert out.read_bytes() == b"hello-devault"
    assert hashlib.sha256(out.read_bytes()).hexdigest() == hashlib.sha256(src.read_bytes()).hexdigest()


def test_local_put_bytes(tmp_path: Path) -> None:
    st = LocalStorage(tmp_path / "root")
    st.put_bytes("k/manifest.json", b'{"x":1}')
    assert st.get_bytes("k/manifest.json") == b'{"x":1}'


def test_local_delete_object_idempotent(tmp_path: Path) -> None:
    st = LocalStorage(tmp_path / "root")
    st.put_bytes("k/x.bin", b"a")
    assert st.exists("k/x.bin")
    st.delete_object("k/x.bin")
    assert not st.exists("k/x.bin")
    st.delete_object("k/x.bin")
    st.delete_object("missing/key")
