from __future__ import annotations

import json
import logging
from typing import Any

_log = logging.getLogger("devault.auth.audit")


def auth_audit(event: str, **fields: Any) -> None:
    """Structured audit line (§十六-08): IP, user, result; ship to log stack in prod."""
    payload = {"event": event, **fields}
    _log.info("%s", json.dumps(payload, default=str))
