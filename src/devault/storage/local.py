from __future__ import annotations

import shutil
from pathlib import Path

from devault.storage.types import Storage


class LocalStorage:
    backend_name = "local"

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        rel = key.lstrip("/").replace("..", "")
        dest = (self.root / rel).resolve()
        root_resolved = self.root.resolve()
        if not str(dest).startswith(str(root_resolved)) or dest == root_resolved:
            raise ValueError(f"Invalid storage key: {key!r}")
        return dest

    def put_file(self, key: str, src_path: Path) -> None:
        dest = self._full_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest)

    def get_file(self, key: str, dest_path: Path) -> None:
        src = self._full_path(key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)

    def put_bytes(self, key: str, data: bytes) -> None:
        dest = self._full_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    def get_bytes(self, key: str) -> bytes:
        return self._full_path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._full_path(key).is_file()
