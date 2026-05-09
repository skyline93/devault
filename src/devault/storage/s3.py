from __future__ import annotations

from pathlib import Path

from botocore.client import BaseClient


class S3Storage:
    """S3-compatible storage. The bucket must already exist (provisioned by ops / IaC)."""

    backend_name = "s3"

    def __init__(self, *, client: BaseClient, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def put_file(self, key: str, src_path: Path) -> None:
        self.client.upload_file(str(src_path), self.bucket, key)

    def get_file(self, key: str, dest_path: Path) -> None:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(dest_path))

    def put_bytes(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def get_bytes(self, key: str) -> bytes:
        resp = self.client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
