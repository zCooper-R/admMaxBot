from __future__ import annotations

import contextvars
import uuid
from logging import Filter, LogRecord

from django.http import HttpRequest, HttpResponse

_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestIDFilter(Filter):
    def filter(self, record: LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            _request_id_ctx.reset(token)
