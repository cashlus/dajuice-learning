#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small, fail-open Tavily helper for diagnosis reference context."""

from __future__ import annotations

import os

from quota_manager import quota_manager


def search_and_context(
    query: str,
    *,
    timeout: int = 10,
    quota_token: str | None = None,
) -> str:
    """Return up to three title/content blocks, or an empty string on any failure."""
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key or not query.strip():
        return ""

    # Quota errors intentionally escape the fail-open Tavily error handling.
    quota_manager.consume(quota_token, "tavily")

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        payload = client.search(
            query=query,
            search_depth="basic",
            max_results=3,
            timeout=timeout,
        )
    except Exception:
        return ""

    results = payload.get("results", []) if isinstance(payload, dict) else []
    blocks: list[str] = []
    for item in results[:3]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        if title or content:
            blocks.append(f"标题：{title}\n内容：{content}")
    return "\n\n".join(blocks)
