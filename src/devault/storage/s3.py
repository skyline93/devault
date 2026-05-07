from __future__ import annotations

from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError


class S3Storage:
    backend_name = "s3"

    def __init__(
        self,
        *,
        endpoint_url: str | None,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str,
        use_ssl: bool,
    ) -> None:
        self.bucket = bucket
        session = boto3.session.Session()
        self.client: BaseClient = session.client(
            "s3",
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            use_ssl=use_ssl,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return
        except ClientError:
            pass
        try:
            self.client.create_bucket(Bucket=self.bucket)
        except ClientError as e2:
            code = e2.response.get("Error", {}).get("Code", "")
            if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise

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
