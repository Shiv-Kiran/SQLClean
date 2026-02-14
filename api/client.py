"""Simple HTTP client helpers for SQLClean API mode."""

import json
from typing import Any, Dict
from urllib import request as urllib_request


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def optimize_sql_via_api(base_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    target = base_url.rstrip("/") + "/v1/optimize"
    return _post_json(target, payload)

