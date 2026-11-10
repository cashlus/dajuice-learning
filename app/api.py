#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI wrapper for the agenda-setting learning loop.

This module intentionally contains no diagnosis, state, or feedback logic of
its own. It only composes the existing modules so the Streamlit demo remains
untouched and independently runnable.
"""

from __future__ import annotations

import hashlib
import os
import sys
import threading
from pathlib import Path
from typing import Literal

# The Codex Windows runtime exposes pydantic through a user-site directory that
# can contain encrypted AppX placeholders. Disabling optional pydantic plugin
# discovery avoids reading those unrelated dist-info files. This is set before
# FastAPI/pydantic is imported and does not affect the application schema.
os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "1")

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from auth import AuthMiddleware  # noqa: E402
from diagnosis_runner import DEFAULT_CARD_PATH, diagnose  # noqa: E402
from feedback_v3 import (  # noqa: E402
    generate_feedback_v3,
    load_json,
    repair_diagnosis_coverage,
)
from state_tracker import LearningSession  # noqa: E402
from library_api import router as library_router  # noqa: E402
from quota_manager import QuotaExceeded, quota_manager  # noqa: E402


CONCEPT_SLUG = "agenda-setting"
SESSION_STATUSES = ("PASS", "NEED_RETRY", "NEED_RECONFIRM")


class DiagnoseRequest(BaseModel):
    claim: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=128)


class DiagnoseResponse(BaseModel):
    status: Literal["PASS", "NEED_RETRY", "NEED_RECONFIRM"]
    feedback: str
    missing_elements: list[str]
    search_used: bool
    search_notice: str


class ResetRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)


class ResetResponse(BaseModel):
    status: Literal["reset"] = "reset"
    session_id: str


app = FastAPI(
    title="Agenda-Setting Learning Loop API",
    version="1.0.0",
)

# CORS must wrap authentication so browser clients can read 401/429 responses.
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


_sessions: dict[str, LearningSession] = {}
_sessions_lock = threading.Lock()


def _request_token(request: Request) -> str:
    token = str(getattr(request.state, "user_token", "") or "").strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="缺少有效的 User_Token，请重新登录。",
        )
    return token


def _session_key(user_token: str, session_id: str) -> str:
    fingerprint = hashlib.sha256(user_token.encode("utf-8")).hexdigest()[:16]
    return f"{fingerprint}:{session_id}"


def _get_session(user_token: str, session_id: str) -> LearningSession:
    key = _session_key(user_token, session_id)
    with _sessions_lock:
        session = _sessions.get(key)
        if session is None:
            session = LearningSession(CONCEPT_SLUG)
            _sessions[key] = session
        return session


@app.exception_handler(QuotaExceeded)
async def _quota_exceeded_handler(
    _request: Request,
    exc: QuotaExceeded,
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": exc.detail,
            "quota_kind": exc.kind,
            "window": exc.window,
            "used": exc.used,
            "limit": exc.limit,
            "retry_after": exc.retry_after,
        },
        headers={"Retry-After": str(exc.retry_after)},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/check")
def auth_check() -> dict[str, bool]:
    return {"ok": True}


def _redact(value: object) -> str:
    text = str(value)
    for name in ("LLM_API_KEY", "TAVILY_API_KEY"):
        secret = os.environ.get(name, "").strip()
        if secret:
            text = text.replace(secret, "[已隐藏]")
    return text[:1200]


def _run_diagnose(
    claim: str,
    session: LearningSession,
    user_token: str,
) -> DiagnoseResponse:
    diagnosis_result = diagnose(claim, quota_token=user_token)
    parsed = diagnosis_result.get("parsed")
    if not diagnosis_result.get("parse_ok") or not isinstance(parsed, dict):
        detail = diagnosis_result.get("parse_error") or "未返回可解析的 JSON"
        raise RuntimeError(f"诊断结果解析失败：{detail}")

    parsed, _repairs = repair_diagnosis_coverage(
        parsed,
        load_json(DEFAULT_CARD_PATH),
    )
    state_result = session.submit(parsed)
    feedback_result = generate_feedback_v3(
        claim,
        parsed,
        DEFAULT_CARD_PATH,
        log=False,
    )

    status = str(state_result.get("status") or "")
    if status not in SESSION_STATUSES:
        raise RuntimeError(f"状态机返回了未知状态：{status or '<empty>'}")

    return DiagnoseResponse(
        status=status,  # type: ignore[arg-type]
        feedback=str(feedback_result.text).strip(),
        missing_elements=list(state_result.get("missing_list") or []),
        search_used=bool(diagnosis_result.get("reference_context_present")),
        search_notice=str(diagnosis_result.get("search_notice") or "").strip(),
    )


@app.post("/api/diagnose", response_model=DiagnoseResponse)
def api_diagnose(payload: DiagnoseRequest, request: Request) -> DiagnoseResponse:
    user_token = _request_token(request)
    claim = payload.claim.strip()
    if not claim:
        raise HTTPException(status_code=422, detail="claim 不能为空")

    session_id = payload.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id 不能为空")
    # One diagnose request covers one diagnosis + one feedback model call.
    quota_manager.consume(user_token, "diagnosis")
    session = _get_session(user_token, session_id)
    try:
        return _run_diagnose(claim, session, user_token)
    except HTTPException:
        raise
    except QuotaExceeded:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"{type(exc).__name__}: {_redact(exc)}",
        ) from exc


@app.post("/api/reset", response_model=ResetResponse)
def api_reset(payload: ResetRequest, request: Request) -> ResetResponse:
    user_token = _request_token(request)
    session_id = payload.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id 不能为空")
    key = _session_key(user_token, session_id)
    with _sessions_lock:
        _sessions[key] = LearningSession(CONCEPT_SLUG)
    return ResetResponse(session_id=session_id)

# Library/review routes are isolated from the original diagnosis loop.
app.include_router(library_router)
