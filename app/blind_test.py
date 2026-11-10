# -*- coding: utf-8 -*-
"""Blind concept test: judge a user's explanation only against the matched
concept's own source_spans.

Usage:
    python blind_test.py <concept> "<user explanation>"

The concept name may be a Chinese term, an English term_en, or a slug
(file name), matched case-insensitively and fuzzily.
"""

import json
import os
import re
import sys
import unicodedata

APP = os.path.dirname(os.path.abspath(__file__))
KB = os.path.dirname(APP)
CONCEPTS = os.path.join(KB, "concepts")

sys.path.insert(0, APP)
from judge_test import judge_claim, split_sentences, _normalize  # noqa: E402

MODEL = "deepseek-v4-pro"


def norm_key(value):
    text = unicodedata.normalize("NFKC", value or "").lower()
    return re.sub(r"[\s\-_/]+", "", text)


def load_index():
    entries = []
    if not os.path.isdir(CONCEPTS):
        return entries
    for name in sorted(os.listdir(CONCEPTS)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(CONCEPTS, name)
        try:
            with open(path, encoding="utf-8") as handle:
                doc = json.load(handle)
        except (OSError, ValueError):
            continue
        entries.append(
            {
                "path": path,
                "slug": os.path.splitext(name)[0],
                "term": doc.get("term", ""),
                "term_en": doc.get("term_en", ""),
                "doc": doc,
            }
        )
    return entries


def find_concept(entries, query):
    key = norm_key(query)
    if not key:
        return None, "empty"

    for entry in entries:
        for candidate in (entry["slug"], entry["term"], entry["term_en"]):
            if key == norm_key(candidate):
                return entry, "exact"

    scored = []
    for entry in entries:
        for candidate in (entry["slug"], entry["term"], entry["term_en"]):
            candidate_key = norm_key(candidate)
            if candidate_key and (key in candidate_key or candidate_key in key):
                scored.append((abs(len(candidate_key) - len(key)), entry))
                break
    if scored:
        scored.sort(key=lambda item: item[0])
        return scored[0][1], "fuzzy"
    return None, "none"


def check_quote(quote, spans):
    """Return strict / normalized / MISS / empty for the evidence quote."""
    if not quote:
        return {"result": "empty", "strict": False, "normalized": False, "segment_index": None}

    for span in spans:
        if quote in span["text"]:
            return {
                "result": "strict",
                "strict": True,
                "normalized": True,
                "segment_index": span["segment_index"],
            }

    normalized_quote = _normalize(quote)
    if normalized_quote:
        for span in spans:
            if normalized_quote in _normalize(span["text"]):
                return {
                    "result": "normalized",
                    "strict": False,
                    "normalized": True,
                    "segment_index": span["segment_index"],
                }
        haystack = " ".join(_normalize(span["text"]) for span in spans)
        if normalized_quote in haystack:
            return {
                "result": "normalized",
                "strict": False,
                "normalized": True,
                "segment_index": None,
            }

    return {"result": "MISS", "strict": False, "normalized": False, "segment_index": None}


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(argv) < 3:
        emit(
            {
                "status": "error",
                "message": "用法：python blind_test.py <概念名> \"<用户解释>\"",
            }
        )
        return 2

    query, explanation = argv[1], argv[2]
    entries = load_index()
    entry, match_kind = find_concept(entries, query)

    if entry is None:
        emit(
            {
                "status": "not_found",
                "message": "该概念未收录",
                "query": query,
                "available": [item["term"] for item in entries],
            }
        )
        return 0

    missing = [name for name in ("LLM_API_KEY", "LLM_BASE_URL") if not os.environ.get(name)]
    if missing:
        emit(
            {
                "status": "error",
                "message": "未设置环境变量：" + "、".join(missing),
                "concept": entry["term"],
            }
        )
        return 2

    os.environ["LLM_MODEL"] = MODEL

    spans = entry["doc"]["source_spans"]
    sentences = split_sentences(explanation)
    claims = []
    for sentence in sentences:
        result = judge_claim(sentence, spans, entry["doc"].get("stances"))
        claims.append(
            {
                "claim": sentence,
                "verdict": result["verdict"],
                "support_type": result["support_type"],
                "matched_role": result["matched_role"],
                "evidence_quote": result["evidence_quote"],
                "explanation": result["explanation"],
                "tradition_hint": result["tradition_hint"],
                "quote_check": check_quote(result["evidence_quote"], spans),
            }
        )

    emit(
        {
            "status": "ok",
            "concept": {
                "query": query,
                "term": entry["term"],
                "term_en": entry["term_en"],
                "slug": entry["slug"],
                "file": entry["path"],
                "match": match_kind,
            },
            "model": MODEL,
            "spans": [[span["segment_index"], span["role"]] for span in spans],
            "claims": claims,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
