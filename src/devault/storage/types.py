from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Storage(Protocol):
    """Sync storage backend for worker (file paths)."""

    backend_name: str

    def put_file(self, key: str, src_path: Path) -> None:
        """Upload/copy local file at src_path to object key."""

    def get_file(self, key: str, dest_path: Path) -> None:
        """Download object key to local dest_path."""

    def put_bytes(self, key: str, data: bytes) -> None:
        """Write small object (e.g. manifest)."""

    def get_bytes(self, key: str) -> bytes:
        """Read small object."""

    def exists(self, key: str) -> bool:
        ...

    def delete_object(self, key: str) -> None:
        """Remove object at key (idempotent if already absent)."""
