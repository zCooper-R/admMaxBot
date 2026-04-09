from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest


def parse_json_request(request: HttpRequest) -> tuple[dict[str, Any], str | None]:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}, "bad_payload"
    if not isinstance(payload, dict):
        return {}, "bad_payload"
    return payload, None
