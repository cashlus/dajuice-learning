#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bearer-token authentication for the hosted learning API."""

from __future__ import annotations

import hmac
import os
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def _configured_tokens() -> list[str]:
    raw_values = [
        os.environ.get("USER_TOKENS", ""),
        os.environ.get("USER_TOKEN", ""),
    ]
    tokens: list[str] = []
    for raw in raw_values:
        for token in re.split(r"[,\s]+", raw):
            token = token.strip()
            if token and token not in tokens:
                tokens.append(token)
    return tokens


def _extract_bearer_token(header: str | None) -> tuple[str | None, str | None]:
    if not header or not header.strip():
        return None, "缺少 Authorization: Bearer <User_Token>。"

    parts = header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None, "Authorization 格式应为 Bearer <User_Token>。"

    token = parts[1].strip()
    if not token:
        return None, "User_Token 不能为空。"
    return token, None


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate every non-public API request and expose the token to routes."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        if request.method == "OPTIONS" or path in PUBLIC_PATHS:
            return await call_next(request)

        token, error = _extract_bearer_token(request.headers.get("Authorization"))
        if error or token is None:
            return _unauthorized(error or "User_Token 无效。")

        allowed = _configured_tokens()
        if not allowed:
            return _unauthorized("服务端未配置 USER_TOKENS，暂时无法访问。")
        if not any(hmac.compare_digest(token, candidate) for candidate in allowed):
            return _unauthorized("User_Token 无效，请向管理员确认。")

        request.state.user_token = token
        return await call_next(request)
