"""AWS KMS envelope helpers for artifact DEKs (control plane credentials)."""

from __future__ import annotations

import base64

import boto3
from botocore.client import BaseClient

from devault.settings import Settings


def build_kms_client(settings: Settings) -> BaseClient:
    region = settings.kms_region or settings.aws_default_region
    return boto3.session.Session().client("kms", region_name=region)


def generate_aes_data_key(settings: Settings, *, key_id: str) -> tuple[bytes, bytes]:
    """Return plaintext 32-byte AES key and KMS ciphertext blob."""
    kms = build_kms_client(settings)
    resp = kms.generate_data_key(KeyId=key_id, KeySpec="AES_256")
    pt = resp["Plaintext"]
    blob = resp["CiphertextBlob"]
    if not isinstance(pt, (bytes, bytearray)) or len(pt) != 32:
        raise RuntimeError("KMS GenerateDataKey returned unexpected plaintext")
    return bytes(pt), bytes(blob)


def decrypt_aes_data_key(settings: Settings, *, ciphertext_blob: bytes) -> bytes:
    kms = build_kms_client(settings)
    resp = kms.decrypt(CiphertextBlob=ciphertext_blob)
    pt = resp["Plaintext"]
    if not isinstance(pt, (bytes, bytearray)) or len(pt) != 32:
        raise RuntimeError("KMS Decrypt returned unexpected plaintext")
    return bytes(pt)


def kms_ciphertext_blob_from_manifest_b64(b64: str) -> bytes:
    raw = (b64 or "").strip()
    if not raw:
        raise ValueError("empty kms_ciphertext_blob_base64")
    return base64.b64decode(raw, validate=True)
