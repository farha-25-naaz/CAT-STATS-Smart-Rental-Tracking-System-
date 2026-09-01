"""Shared password/PIN hashing context (Phase 4).

passlib's CryptContext.verify is constant-time, so PIN checks don't leak timing.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_pin(pin: str) -> str:
    return pwd_context.hash(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    if not pin_hash:
        return False
    try:
        return pwd_context.verify(pin, pin_hash)
    except ValueError:
        return False
