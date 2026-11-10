#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print the Tavily reference context for one agenda-setting query."""

from __future__ import annotations

import json
import os
import sys

from web_search import search_and_context


def main() -> int:
    query = "算法推荐让我只看到某些新闻"
    key_configured = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    context = search_and_context(query)

    print(
        json.dumps(
            {
                "query": query,
                "key_configured": key_configured,
                "fallback": None if context else ("no_key" if not key_configured else "empty_or_error"),
                "context_chars": len(context),
                "context": context,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
