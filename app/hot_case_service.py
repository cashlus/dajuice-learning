#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-open, cached Tavily wrapper for illustrative current-event cases.

This module is display-only. Its output is never accepted by review_service as
a grading reference. web_search.py is deliberately left untouched because the
existing diagnosis loop depends on its return shape.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quota_manager import quota_manager

ROOT_DIR = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT_DIR / "data" / "hot_cases.json"
CACHE_TTL_SECONDS = 12 * 60 * 60
WARNING = "AI 联网外推，未核验，不能作为判分依据"
_LOCK = threading.RLock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_cache_unlocked() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    try:
        with CACHE_PATH.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _save_cache_unlocked(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = CACHE_PATH.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp, CACHE_PATH)


def _empty_result(term: dict[str, Any], notice: str, *, search_used: bool = False) -> dict[str, Any]:
    return {
        "term_id": str(term.get("term_id") or ""),
        "term_name": str(term.get("name") or ""),
        "case_summary": "",
        "source_urls": [],
        "search_used": search_used,
        "cached": False,
        "notice": notice,
        "ai_unverified": True,
        "warning": WARNING,
        "not_for_grading": True,
        "fetched_at": _now_iso(),
    }


def _build_query(term: dict[str, Any]) -> str:
    name = str(term.get("name") or "").strip()
    definition = str(term.get("definition") or "").strip()
    suffix = "近期 新闻 案例 2025 2026 营销 传播"
    return f'"{name}" {suffix} {definition[:90]}'.strip()


def search_hot_cases(
    term: dict[str, Any],
    *,
    force: bool = False,
    quota_token: str | None = None,
) -> dict[str, Any]:
    """Return cached/search results with mandatory unverified markers.

    Missing keys, network errors and empty result sets all fail open with a
    structured warning. No exception escapes to the API caller.
    """
    term_id = str(term.get("term_id") or "").strip()
    cache_key = term_id or str(term.get("name") or "").strip()
    now = time.time()

    with _LOCK:
        cache = _load_cache_unlocked()
        cached = cache.get(cache_key)
        cached_at = float(cached.get("cached_at") or 0) if isinstance(cached, dict) else 0
        if not force and isinstance(cached, dict) and now - cached_at < CACHE_TTL_SECONDS:
            result = {key: value for key, value in cached.items() if key != "cached_at"}
            result["cached"] = True
            result["ai_unverified"] = True
            result["warning"] = WARNING
            result["not_for_grading"] = True
            return result

    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return _empty_result(term, "未配置 TAVILY_API_KEY，已跳过联网案例。")

    query = _build_query(term)
    # Cache hits and missing keys are free; an actual Tavily attempt is counted.
    quota_manager.consume(quota_token, "tavily")
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        payload = client.search(
            query=query,
            search_depth="basic",
            max_results=4,
            timeout=12,
        )
    except Exception as exc:
        return _empty_result(term, f"联网案例暂时不可用：{type(exc).__name__}")

    results = payload.get("results", []) if isinstance(payload, dict) else []
    snippets: list[str] = []
    source_urls: list[str] = []
    for item in results[:4]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        url = str(item.get("url") or "").strip()
        if title or content:
            snippets.append(f"【{title or '未命名来源'}】{content[:420]}")
        if url and url not in source_urls:
            source_urls.append(url)

    if not snippets:
        return _empty_result(term, "联网搜索没有返回可用案例。", search_used=True)

    result = {
        "term_id": term_id,
        "term_name": str(term.get("name") or ""),
        "case_summary": "\n\n".join(snippets)[:2200],
        "source_urls": source_urls[:4],
        "search_used": True,
        "cached": False,
        "notice": "以下内容来自公开网络检索整理，只用于帮助联想，不参与判分。",
        "ai_unverified": True,
        "warning": WARNING,
        "not_for_grading": True,
        "fetched_at": _now_iso(),
    }
    with _LOCK:
        cache = _load_cache_unlocked()
        cache[cache_key] = {**result, "cached_at": now}
        _save_cache_unlocked(cache)
    return result
