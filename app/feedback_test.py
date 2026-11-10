# -*- coding: utf-8 -*-
"""Generate and inspect five-field feedback from recorded frozen verdicts."""

import json
import os
import sys

APP = os.path.dirname(os.path.abspath(__file__))
KB = r"C:\Users\cashrus\Documents\Codex\.kb"
if APP not in sys.path:
    sys.path.insert(0, APP)

from judge_test import _normalize
from feedback import generate_feedback, severity_for

CASES = [
    {
        "case_id": "fb-liberty-01",
        "concept": "liberty",
        "claim": "自由就是人可以自由地做任何不违背自我道德的事，不损害他人",
        "judged": {
            "verdict": "属于另一诠释",
            "support_type": "none",
            "matched_role": "",
            "evidence_quote": "",
            "tradition_hint": "道德化自由观：自由不仅是无干涉，还要求行为不违背自我道德",
        },
    },
    {
        "case_id": "fb-justice-01",
        "concept": "justice",
        "claim": "公正就是按照社会理性公允的价值观念，对那些有害于公众的进行审判，对那些有利于公众的进行奖赏",
        "judged": {
            "verdict": "属于另一诠释",
            "support_type": "none",
            "matched_role": "",
            "evidence_quote": "",
            "tradition_hint": "功利主义（Mill、Sidgwick、Bentham）：正义的要求应大致等同于能带来最大幸福的规则，正义本身可由效用加以解释。",
        },
    },
]


def load_concept(slug):
    path = os.path.join(KB, "concepts", slug + ".json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def quote_check(quote, concept):
    spans = concept.get("source_spans") or []
    if not quote:
        return "empty"
    if any(quote in (s.get("text") or "") for s in spans):
        return "strict"
    normalized_quote = _normalize(quote)
    if any(normalized_quote in _normalize(s.get("text") or "") for s in spans):
        return "normalized"
    return "MISS"


def direction_check(direction, verdict, tradition_hint, concept):
    if verdict != "属于另一诠释":
        return {
            "consistent": direction == "",
            "reason": "非“属于另一诠释”时 direction 应为空",
        }
    if not direction:
        return {"consistent": False, "reason": "属于另一诠释但 direction 为空"}
    stances = concept.get("stances") or []
    exact_stance = direction in stances
    relates_to_hint = bool(tradition_hint) and (
        direction == tradition_hint
        or _normalize(direction) == _normalize(tradition_hint)
        or _normalize(direction) in _normalize(tradition_hint)
        or _normalize(tradition_hint) in _normalize(direction)
    )
    return {
        "consistent": bool(relates_to_hint),
        "exact_stance": exact_stance,
        "relates_to_tradition_hint": relates_to_hint,
        "reason": "direction 应基于 tradition_hint 对应 stance 原文",
    }


def main():
    if not os.environ.get("LLM_API_KEY") or not os.environ.get("LLM_BASE_URL"):
        print("LLM_API_KEY / LLM_BASE_URL 未设置，无法运行测试。")
        return 2

    for case in CASES:
        concept = load_concept(case["concept"])
        judged = dict(case["judged"])
        feedback = generate_feedback(
            case["claim"],
            judged["verdict"],
            judged["support_type"],
            judged["matched_role"],
            judged["evidence_quote"],
            judged["tradition_hint"],
            concept,
        )
        expected_severity = severity_for(judged["verdict"], judged["support_type"])
        checks = {
            "standard_def_quote": quote_check(feedback.get("standard_def", ""), concept),
            "severity_expected": expected_severity,
            "severity_consistent": feedback.get("severity") == expected_severity,
            "direction": direction_check(
                feedback.get("direction", ""),
                judged["verdict"],
                judged["tradition_hint"],
                concept,
            ),
        }
        print("=" * 80)
        print("case_id:", case["case_id"])
        print("concept:", case["concept"])
        print("claim:", case["claim"])
        print("\n[judge]")
        print(json.dumps(judged, ensure_ascii=False, indent=2))
        print("\n[feedback five fields]")
        print(json.dumps(feedback, ensure_ascii=False, indent=2))
        print("\n[checks]")
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
