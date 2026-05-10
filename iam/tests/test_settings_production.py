from __future__ import annotations

import pytest


def test_production_requires_jwt_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from devault_iam.settings import Settings, clear_settings_cache

    monkeypatch.setenv("IAM_ENVIRONMENT", "production")  # field: environment
    monkeypatch.setenv("IAM_JWT_ISSUER", "https://iam.example/")
    monkeypatch.setenv("IAM_JWT_PRIVATE_KEY", "")
    monkeypatch.setenv("IAM_JWT_PUBLIC_KEY", "")
    monkeypatch.delenv("IAM_JWT_PRIVATE_KEY_FILE", raising=False)
    monkeypatch.delenv("IAM_JWT_PUBLIC_KEY_FILE", raising=False)
    clear_settings_cache()
    s = Settings()
    with pytest.raises(RuntimeError, match="IAM_JWT_PRIVATE_KEY"):
        s.assert_production_config()


def test_production_requires_https_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    from devault_iam.settings import Settings, clear_settings_cache

    monkeypatch.setenv("IAM_ENVIRONMENT", "production")  # field: environment
    monkeypatch.setenv("IAM_JWT_ISSUER", "http://insecure.example/")
    monkeypatch.setenv("IAM_JWT_PRIVATE_KEY", "dummy-pem")
    monkeypatch.setenv("IAM_JWT_PUBLIC_KEY", "dummy-pem")
    clear_settings_cache()
    s = Settings()
    with pytest.raises(RuntimeError, match="https"):
        s.assert_production_config()
