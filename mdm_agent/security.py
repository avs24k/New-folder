import hashlib
import hmac
import json
from typing import Any


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def verify_hmac(payload: dict[str, Any], provided_sig: str, secret: str) -> bool:
    if not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), canonical_json(payload), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_sig)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
