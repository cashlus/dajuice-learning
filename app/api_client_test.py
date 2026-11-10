#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke-test the FastAPI wrapper with the three core classroom cases."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "1")

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from fastapi.testclient import TestClient

from api import app


CASES = [
    {
        "name": "大白话",
        "session_id": "api-smoke-colloquial",
        "claim": (
            "媒体天天播什么，老百姓就觉得什么事情重要，"
            "不仅觉得事重要，还觉得这事是好是坏。"
        ),
    },
    {
        "name": "跑题",
        "session_id": "api-smoke-offtopic",
        "claim": "人们因为害怕被孤立，所以不敢表达少数意见。",
    },
    {
        "name": "完美通关",
        "session_id": "api-smoke-perfect",
        "claim": (
            "议程设置研究媒体通过报道频率和版面等方式，对某些对象或属性给予更高显著性，"
            "公众对这些对象的重要性排序或属性判断随之发生变化，核心机制是媒体显著性"
            "向公众显著性的转移；它区分第一层对象显著性、第二层属性显著性和网络议程设置，"
            "并且不直接决定公众支持谁或持什么立场，也不等同于启动效应。"
        ),
    },
]


def main() -> int:
    if not os.environ.get("LLM_API_KEY", "").strip():
        print("LLM_API_KEY 未设置，无法执行真实 API 冒烟测试。", file=sys.stderr)
        return 2

    client = TestClient(app)
    required_keys = {
        "status",
        "feedback",
        "missing_elements",
        "search_used",
        "search_notice",
    }

    for case in CASES:
        reset = client.post(
            "/api/reset",
            json={"session_id": case["session_id"]},
        )
        reset.raise_for_status()
        response = client.post(
            "/api/diagnose",
            json={"claim": case["claim"], "session_id": case["session_id"]},
        )
        print(f"=== {case['name']} / HTTP {response.status_code} ===")
        if response.status_code != 200:
            print(response.text)
            return 1

        payload = response.json()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        missing_keys = required_keys.difference(payload)
        if missing_keys:
            print(f"缺少响应字段：{sorted(missing_keys)}", file=sys.stderr)
            return 1
        if not isinstance(payload["missing_elements"], list):
            print("missing_elements 不是数组", file=sys.stderr)
            return 1
        if not isinstance(payload["search_used"], bool):
            print("search_used 不是布尔值", file=sys.stderr)
            return 1

    print("API 冒烟测试完成：3 个用例均返回 200，响应结构齐全。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
