#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal v3 diagnosis runner with optional Tavily reference context."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from quota_manager import QuotaExceeded
from web_search import search_and_context


APP_DIR = Path(__file__).resolve().parent
DEFAULT_PROMPT_PATH = APP_DIR / "prompts" / "diagnosis_prompt.md"
DEFAULT_CARD_PATH = APP_DIR.parent / "v2" / "agenda-setting.json"
SHORT_CLAIM_CHARS = 10

_UNUSABLE_CONTEXT_MARKERS = (
    "err-",
    "error",
    "exception",
    "traceback",
    "服务器内部错误",
    "页面无法解析",
    "无法解析",
    "乱码",
    "搜索失败",
    "请求失败",
    "无法访问",
    "internal server error",
    "bad gateway",
    "service unavailable",
    "access denied",
    "not found",
)


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层不是对象: {path}")
    return value


def should_search(claim: str, *, force_search: bool = False) -> bool:
    compact = re.sub(r"\s+", "", claim)
    return force_search or len(compact) < SHORT_CLAIM_CHARS


def is_usable_reference_context(context: str) -> bool:
    """Reject clearly broken or irrelevant search snippets before prompting."""
    text = re.sub(r"\s+", " ", str(context or "")).strip()
    if len(text) < 24:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in _UNUSABLE_CONTEXT_MARKERS):
        return False
    if re.search(r"([^\w\s\u4e00-\u9fff])\1{2,}", text):
        return False
    allowed_punctuation = set("，。！？；：、“”‘’（）【】《》,.!?;:'\"()-")
    symbol_count = sum(
        1
        for char in text
        if not char.isalnum()
        and not char.isspace()
        and char not in allowed_punctuation
        and not ("\u4e00" <= char <= "\u9fff")
    )
    return symbol_count / len(text) <= 0.22


def build_messages(
    claim: str,
    knowledge_card: dict[str, Any],
    prompt_path: str | Path = DEFAULT_PROMPT_PATH,
    *,
    reference_context: str = "",
) -> list[dict[str, str]]:
    template = Path(prompt_path).read_text(encoding="utf-8")
    payload: dict[str, Any] = {"claim": claim, "knowledge_card": knowledge_card}
    if reference_context.strip():
        payload["reference_context"] = reference_context.strip()
    user_content = (
        "请严格按规则诊断以下输入，只输出一个 JSON 对象：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    return [
        {"role": "system", "content": template},
        {"role": "user", "content": user_content},
    ]


def _endpoint(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def _chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str,
    max_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("LLM_API_KEY 未设置")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        _endpoint(base_url),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise RuntimeError(
            f"LLM 请求超时（{timeout} 秒），请稍后重试或缩短输入。"
        ) from exc
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
            raise RuntimeError(
                f"LLM 请求超时（{timeout} 秒），请稍后重试或缩短输入。"
            ) from exc
        raise RuntimeError(f"LLM 连接失败: {exc}") from exc

    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("LLM 返回中没有 choices")
    choice = choices[0] or {}
    content = (choice.get("message") or {}).get("content") or ""
    finish_reason = choice.get("finish_reason")
    if str(finish_reason or "").lower() in {"length", "max_tokens"}:
        raise RuntimeError(
            "LLM 输出被截断（finish_reason=length），请缩短题目或提高 max_tokens。"
        )
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM 返回内容为空")
    return {
        "content": content.strip(),
        "returned_model": payload.get("model"),
        "finish_reason": finish_reason,
        "usage": payload.get("usage") or {},
    }


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.S)
    if fenced:
        cleaned = fenced.group(1).strip()
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("未找到 JSON 对象")
    obj, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    if not isinstance(obj, dict):
        raise ValueError("顶层不是 JSON 对象")
    return obj


def diagnose(
    claim: str,
    *,
    card_path: str | Path = DEFAULT_CARD_PATH,
    prompt_path: str | Path = DEFAULT_PROMPT_PATH,
    model: str | None = None,
    max_tokens: int | None = None,
    timeout: int = 120,
    force_search: bool = False,
    quota_token: str | None = None,
    search_fn: Callable[..., str] = search_and_context,
) -> dict[str, Any]:
    claim = claim.strip()
    if not claim:
        raise ValueError("claim 不能为空")
    card = load_json(card_path)
    requested_model = model or os.environ.get("LLM_MODEL", "deepseek-chat")
    token_limit = max_tokens or int(os.environ.get("LLM_MAX_TOKENS", "4000"))

    search_attempted = should_search(claim, force_search=force_search)
    reference_context = ""
    search_elapsed_ms = 0
    search_notice = ""
    if search_attempted:
        search_started = time.perf_counter()
        try:
            if quota_token and search_fn is search_and_context:
                candidate = str(
                    search_fn(claim, quota_token=quota_token) or ""
                ).strip()
            else:
                candidate = str(search_fn(claim) or "").strip()
            if candidate and is_usable_reference_context(candidate):
                reference_context = candidate
            elif candidate:
                search_notice = "搜索到的资料似乎无关，请重新提供。已改用知识卡判断。"
        except QuotaExceeded:
            raise
        except Exception:
            search_notice = "联网检索失败，已改用知识卡判断。"
        search_elapsed_ms = round((time.perf_counter() - search_started) * 1000)

    messages = build_messages(
        claim, card, prompt_path, reference_context=reference_context
    )
    started = time.perf_counter()
    response = _chat_completion(
        messages, model=requested_model, max_tokens=token_limit, timeout=timeout
    )
    elapsed_seconds = round(time.perf_counter() - started, 3)

    parsed: dict[str, Any] | None = None
    parse_error: str | None = None
    try:
        parsed = extract_json(response["content"])
        parse_ok = True
    except Exception as exc:
        parse_ok = False
        parse_error = f"{type(exc).__name__}: {exc}"

    return {
        "claim": claim,
        "requested_model": requested_model,
        "returned_model": response.get("returned_model"),
        "finish_reason": response.get("finish_reason"),
        "usage": response.get("usage") or {},
        "elapsed_seconds": elapsed_seconds,
        "search_attempted": search_attempted,
        "search_elapsed_ms": search_elapsed_ms,
        "search_notice": search_notice,
        "reference_context_present": bool(reference_context.strip()),
        "reference_context_chars": len(reference_context.strip()),
        "parse_ok": parse_ok,
        "parse_error": parse_error,
        "content": response["content"],
        "parsed": parsed,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="agenda-setting v3 diagnosis runner")
    parser.add_argument("--claim", required=True)
    parser.add_argument("--card", default=str(DEFAULT_CARD_PATH))
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL", "deepseek-chat"))
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--force-search", action="store_true")
    parser.add_argument("--prompt-only", action="store_true")
    args = parser.parse_args()

    claim = args.claim.strip()
    if not claim:
        print("[diagnosis_runner] claim 为空", file=sys.stderr)
        return 2

    if args.prompt_only:
        search_triggered = should_search(claim, force_search=args.force_search)
        context = ""
        search_notice = ""
        if search_triggered:
            try:
                candidate = str(search_and_context(claim) or "").strip()
                if candidate and is_usable_reference_context(candidate):
                    context = candidate
                elif candidate:
                    search_notice = "搜索到的资料似乎无关，请重新提供。已改用知识卡判断。"
            except Exception:
                search_notice = "联网检索失败，已改用知识卡判断。"
        card = load_json(args.card)
        messages = build_messages(claim, card, args.prompt, reference_context=context)
        print(
            json.dumps(
                {
                    "claim": claim,
                    "search_attempted": search_triggered,
                    "search_notice": search_notice,
                    "reference_context_present": bool(context.strip()),
                    "reference_context_chars": len(context.strip()),
                    "prompt_contains_ai_judged": "ai_judged" in messages[0]["content"],
                    "prompt_contains_uncovered_dimensions": "uncovered_dimensions"
                    in messages[0]["content"],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        print("=== SYSTEM ===")
        print(messages[0]["content"])
        print("=== USER ===")
        print(messages[1]["content"])
        return 0

    try:
        result = diagnose(
            claim,
            card_path=args.card,
            prompt_path=args.prompt,
            model=args.model,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            force_search=args.force_search,
        )
    except Exception as exc:
        print(f"[diagnosis_runner] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
