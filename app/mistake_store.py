#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small JSON-backed mistake notebook with spaced review intervals.

The store is intentionally local and dependency free. It is safe to use from
FastAPI's threadpool: all reads/writes are guarded and writes are atomic.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
MISTAKE_DIR = ROOT_DIR / "data" / "mistakes"
MISTAKE_PATH = MISTAKE_DIR / "mistakes.json"

REVIEW_INTERVALS_DAYS = (1, 3, 7, 15)
_LOCK = threading.RLock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _read_unlocked() -> list[dict[str, Any]]:
    if not MISTAKE_PATH.exists():
        return []
    try:
        with MISTAKE_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, dict):
        payload = payload.get("mistakes", [])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _write_unlocked(items: list[dict[str, Any]]) -> None:
    MISTAKE_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix="mistakes-",
        suffix=".tmp",
        dir=str(MISTAKE_DIR),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(items, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, MISTAKE_PATH)
    finally:
        if os.path.exists(temp_name):
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def _sorted(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            _parse_iso(item.get("next_review_at")) or datetime.max.replace(tzinfo=timezone.utc),
            str(item.get("created_at") or ""),
        ),
    )


def add_mistake(
    question: dict[str, Any],
    grade: dict[str, Any],
    user_answer: str,
) -> dict[str, Any]:
    """Record a wrong answer and return the stored row.

    A repeated wrong answer to the same generated question updates the existing
    row instead of creating duplicate cards.
    """
    now = _now()
    question_id = str(question.get("question_id") or "").strip()
    with _LOCK:
        items = _read_unlocked()
        existing = next(
            (item for item in items if question_id and item.get("question_id") == question_id),
            None,
        )
        next_review = _iso(now + timedelta(days=REVIEW_INTERVALS_DAYS[0]))
        base = existing or {}
        record = {
            "id": str(base.get("id") or f"m-{uuid.uuid4().hex}"),
            "book_id": str(question.get("book_id") or base.get("book_id") or ""),
            "chapter_id": str(question.get("chapter_id") or base.get("chapter_id") or ""),
            "term_id": str(question.get("term_id") or base.get("term_id") or ""),
            "question": str(question.get("question") or base.get("question") or ""),
            "question_type": str(question.get("type") or base.get("question_type") or "short_answer"),
            "user_answer": str(user_answer or "").strip(),
            "correct_answer": str(
                grade.get("correct_answer")
                or question.get("correct_answer")
                or base.get("correct_answer")
                or ""
            ),
            "reason": str(grade.get("grading_reason") or base.get("reason") or ""),
            "missing_points": list(
                grade.get("missing_points") or base.get("missing_points") or []
            ),
            "created_at": str(base.get("created_at") or _iso(now)),
            "next_review_at": next_review,
            "review_count": int(base.get("review_count") or 0) + (1 if existing else 0),
            "question_id": question_id or str(base.get("question_id") or ""),
            "options": list(question.get("options") or base.get("options") or []),
            "reference_excerpt": str(
                question.get("reference_excerpt") or grade.get("reference_excerpt") or ""
            ),
            "key_points": list(question.get("key_points") or base.get("key_points") or []),
            "common_confusions": list(
                question.get("common_confusions") or base.get("common_confusions") or []
            ),
            "option_term_map": dict(
                question.get("option_term_map") or base.get("option_term_map") or {}
            ),
            "term_name": str(question.get("term_name") or base.get("term_name") or ""),
            "book_title": str(question.get("book_title") or base.get("book_title") or ""),
            "chapter_title": str(question.get("chapter_title") or base.get("chapter_title") or ""),
            "last_reviewed_at": str(base.get("last_reviewed_at") or ""),
        }
        if existing:
            items[items.index(existing)] = record
        else:
            items.append(record)
        _write_unlocked(items)
        return dict(record)


def list_mistakes() -> list[dict[str, Any]]:
    with _LOCK:
        return _sorted([dict(item) for item in _read_unlocked()])


def list_due_mistakes(now: datetime | None = None) -> list[dict[str, Any]]:
    moment = now or _now()
    due: list[dict[str, Any]] = []
    with _LOCK:
        for item in _read_unlocked():
            due_at = _parse_iso(item.get("next_review_at"))
            if due_at is None or due_at <= moment:
                due.append(dict(item))
    return _sorted(due)


def get_mistake(mistake_id: str) -> dict[str, Any] | None:
    target = str(mistake_id or "").strip()
    if not target:
        return None
    with _LOCK:
        for item in _read_unlocked():
            if str(item.get("id") or "") == target:
                return dict(item)
    return None


def review_mistake(mistake_id: str, correct: bool) -> dict[str, Any] | None:
    target = str(mistake_id or "").strip()
    if not target:
        return None
    now = _now()
    with _LOCK:
        items = _read_unlocked()
        for index, item in enumerate(items):
            if str(item.get("id") or "") != target:
                continue
            old_count = int(item.get("review_count") or 0)
            if correct:
                interval_index = min(old_count, len(REVIEW_INTERVALS_DAYS) - 1)
                days = REVIEW_INTERVALS_DAYS[interval_index]
            else:
                days = REVIEW_INTERVALS_DAYS[0]
            item = dict(item)
            item["review_count"] = old_count + 1
            item["last_reviewed_at"] = _iso(now)
            item["next_review_at"] = _iso(now + timedelta(days=days))
            item["last_review_result"] = "correct" if correct else "incorrect"
            items[index] = item
            _write_unlocked(items)
            return item
    return None


def mistake_stats() -> dict[str, int]:
    items = list_mistakes()
    due = list_due_mistakes()
    return {
        "total": len(items),
        "due": len(due),
        "reviewing": sum(1 for item in items if int(item.get("review_count") or 0) > 0),
    }