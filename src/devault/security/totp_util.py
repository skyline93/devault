from __future__ import annotations

import pyotp


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(*, secret: str, email: str, issuer: str = "DeVault") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    c = code.strip().replace(" ", "")
    if not c.isdigit() or len(c) not in (6, 8):
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(c, valid_window=1)
