from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_MIN_PASSWORD_LEN = 12

_ph = PasswordHasher()


def assert_password_policy(plain: str) -> None:
    if len(plain) < _MIN_PASSWORD_LEN:
        raise ValueError(f"password must be at least {_MIN_PASSWORD_LEN} characters")


def hash_password(plain: str) -> str:
    assert_password_policy(plain)
    return _ph.hash(plain)


def verify_password(hash_str: str, plain: str) -> bool:
    try:
        return _ph.verify(hash_str, plain)
    except VerifyMismatchError:
        return False
