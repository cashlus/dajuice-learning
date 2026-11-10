# -*- coding: utf-8 -*-
"""Generate structured pedagogical feedback on top of a frozen verdict.

The verdict pipeline is frozen: this module never re-judges the claim. It only
turns (claim, verdict, support_type, matched_role, evidence_quote,
tradition_hint, concept) into a five-field feedback object.

Public API:
    generate_feedback(claim, verdict, support_type, matched_role,
                      evidence_quote, tradition_hint, concept) -> dict

Required environment variables:
    LLM_API_KEY   - bearer token
    LLM_BASE_URL  - OpenAI-compatible base URL, e.g. https://host/v1
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

APP = os.path.dirname(os.path.abspath(__file__))
if APP not in sys.path:
    sys.path.insert(0, APP)

from judge_test import _endpoint, _extract_json  # noqa: E402

MODEL = "deepseek-v4-pro"
SEVERITIES = ("错误", "偏离", "非主流", "无偏差")
FIELDS = ("restatement", "standard_def", "deviation", "severity", "direction")

SYSTEM_PROMPT = (
    "你是哲学概念学习应用中的反馈生成器。你只能依据给定的 concept"
    "（source_spans 与 stances）生成反馈，不得引入任何外部知识、常识或哲学史记忆。\n"
    "字段要求：\n"
    "1. restatement：用一句中文复述用户的核心主张，不加评价。\n"
    "2. standard_def：必须先根据 claim 的主题从 source_spans 中选择最接近的段落，不能默认取第一段；"
    "若 claim 涉及自由的界限、伤害、干涉、法律或他人，优先选讲 absence of obstacles、"
    "without interference 或 external constraints 的段落；若 claim 涉及自我实现、自律、"
    "真实自我或自我决定，优先选讲 self-determination 或 self-realization 的段落。"
    "然后摘取该段中与 claim 最相关的一句定义，必须是原文中连续出现的逐字子串，"
    "不得改写、不得拼接、不得翻译；没有合适定义句时引用最接近的一段原文。\n"
    "3. deviation：必须写成“用户说了 X，参照定义是 Y，区别在于 Z”，具体指出加了什么限定、"
    "换了什么标准、或把什么当成了什么，不得泛泛说“有偏差”。\n"
    "4. severity：只能是 错误、偏离、非主流、无偏差 之一。判断标准：verdict=矛盾→错误；"
    "verdict=支持且 support_type=inference→偏离（加了推论）；verdict=属于另一诠释→非主流；"
    "verdict=未被覆盖→偏离（参照段未覆盖但可能正确）；"
    "verdict=支持且 support_type=direct/synonym→无偏差。\n"
    "5. direction：仅当 verdict=属于另一诠释 时非空；内容必须基于 tradition_hint 对应 stance 的原文，"
    "指出该传统及其学术地位；其他 verdict 一律空字符串。\n"
    "只输出一个 JSON 对象，不要输出解释性文字、不要加代码块标记。"
)


def severity_for(verdict, support_type):
    if verdict == "矛盾":
        return "错误"
    if verdict == "支持" and support_type == "inference":
        return "偏离"
    if verdict == "属于另一诠释":
        return "非主流"
    if verdict == "未被覆盖":
        return "偏离"
    return "无偏差"


def _clip(text, limit=160):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _first_sentence(text):
    text = (text or "").strip()
    match = re.search(r"[.!?](?=\s|$)", text)
    if match and match.end() >= 40:
        return text[: match.end()]
    return text


def _fallback_standard(concept):
    spans = concept.get("source_spans") or []
    if not spans:
        return ""
    span = next((s for s in spans if s.get("role") == "primary_def"), spans[0])
    return _first_sentence(span.get("text", ""))


def _exact_quote(quote, concept):
    """Return the source substring when the model differs only in whitespace."""
    quote = (quote or "").strip()
    if not quote:
        return quote
    for span in concept.get("source_spans") or []:
        text = span.get("text") or ""
        if quote in text:
            return quote
        tokens = quote.split()
        if tokens:
            pattern = r"\s+".join(re.escape(token) for token in tokens)
            match = re.search(pattern, text)
            if match:
                return match.group(0)
    return quote


def _degraded(claim, verdict, support_type, matched_role, evidence_quote,
              tradition_hint, concept, error=""):
    standard = _exact_quote(_fallback_standard(concept), concept)
    severity = severity_for(verdict, support_type)
    if evidence_quote:
        deviation = (
            "用户说了「%s」，参照定义是「%s」，区别在于判定引用的原文是「%s」，"
            "两者的措辞与限定不一致。" % (_clip(claim), _clip(standard), _clip(evidence_quote))
        )
    else:
        deviation = (
            "用户说了「%s」，参照定义是「%s」，区别在于判定结果为“%s”（support_type=%s），"
            "该说法与参照定义的核心标准不对应。" % (_clip(claim), _clip(standard), verdict, support_type)
        )
    return {
        "restatement": claim.strip(),
        "standard_def": standard,
        "deviation": deviation,
        "severity": severity,
        "direction": tradition_hint if verdict == "属于另一诠释" else "",
    }


def _stance_block(concept):
    stances = concept.get("stances") or []
    if not stances:
        return "（无）"
    return "\n".join("- " + s for s in stances)


def build_prompt(claim, verdict, support_type, matched_role, evidence_quote,
                 tradition_hint, concept):
    spans = concept.get("source_spans") or []
    blocks = []
    for i, span in enumerate(spans, 1):
        blocks.append(
            "[%d] role=%s segment_index=%s\n%s"
            % (i, span.get("role", ""), span.get("segment_index", ""),
               (span.get("text") or "").strip())
        )
    expected_severity = severity_for(verdict, support_type)
    return (
        "概念：%s（%s）\n概念简述：%s\n\n"
        % (concept.get("term", ""), concept.get("term_en", ""), concept.get("short_def", ""))
        + "source_spans:\n\n"
        + "\n\n".join(blocks)
        + "\n\nstances:\n"
        + _stance_block(concept)
        + "\n\n判定结果（已冻结，不得更改）：\n"
        + "verdict=%s\nsupport_type=%s\nmatched_role=%s\nevidence_quote=%s\ntradition_hint=%s\n"
        % (verdict, support_type, matched_role or "", evidence_quote or "", tradition_hint or "")
        + "\n用户原话：\n"
        + claim.strip()
        + "\n\n输出 JSON（五个字段，全部为字符串）：\n"
        + '{"restatement": "...", "standard_def": "...", "deviation": "...", '
        + '"severity": "%s", "direction": "..."}\n' % expected_severity
        + "硬性要求：\n"
        + "1. standard_def 必须先从上面 source_spans 中按 claim 主题选最接近的段落，不能默认取第一段；"
        + "claim 涉及界限、伤害、干涉、法律或他人时，优先选讲 absence of obstacles、without interference "
        + "或 external constraints 的段落；claim 涉及自我实现、自律、真实自我时，优先选讲 self-determination "
        + "或 self-realization 的段落；再从该段摘取连续逐字子串，不得改写、不得拼接、不得翻译；\n"
        + "2. deviation 必须写成“用户说了 X，参照定义是 Y，区别在于 Z”，具体到限定词、标准或归类；\n"
        + "3. severity 必须严格等于「%s」；\n" % expected_severity
        + "4. direction 仅在 verdict=\"属于另一诠释\" 时非空，且必须基于上面 stances 的原文；否则为空字符串。"
    )


def _chat(user_prompt):
    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    if not base_url or not api_key:
        raise RuntimeError("LLM_BASE_URL / LLM_API_KEY 未设置")
    payload = {
        "model": MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    request = urllib.request.Request(
        _endpoint(base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        body = json.loads(response.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    return _extract_json(content)


def generate_feedback(claim, verdict, support_type, matched_role,
                      evidence_quote, tradition_hint, concept):
    """Return the five feedback fields; never raise on LLM/parse failure."""
    fallback = _degraded(
        claim, verdict, support_type, matched_role, evidence_quote,
        tradition_hint, concept,
    )
    try:
        prompt = build_prompt(
            claim, verdict, support_type, matched_role, evidence_quote,
            tradition_hint, concept,
        )
        result = _chat(prompt)
    except (urllib.error.URLError, KeyError, ValueError, TypeError,
            json.JSONDecodeError, RuntimeError, OSError) as exc:
        fallback["deviation"] = (
            "[反馈生成降级：%s] " % type(exc).__name__
        ) + fallback["deviation"]
        return fallback

    output = dict(fallback)
    for key in FIELDS:
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            output[key] = value.strip()

    if output["severity"] not in SEVERITIES:
        output["severity"] = severity_for(verdict, support_type)
    output["standard_def"] = _exact_quote(output["standard_def"], concept)
    if verdict != "属于另一诠释":
        output["direction"] = ""
    elif tradition_hint:
        output["direction"] = tradition_hint
    elif not output["direction"]:
        output["direction"] = ""
    return output


# Agenda-setting v3 learning-loop feedback facade.
#
# The legacy five-field API above is kept intact for app.py and
# feedback_test.py. New callers should use generate_feedback_v3(), which
# accepts the frozen point-level diagnosis and returns validated natural
# language plus usage metadata.
from feedback_v3 import (  # noqa: E402,F401
    FeedbackResult,
    generate_feedback_v3,
    render_feedback_prompt,
    strip_diagnosis,
    validate_diagnosis_input,
    validate_feedback_text,
)
