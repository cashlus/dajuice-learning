#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agenda-setting v3 learning-loop feedback layer.

The diagnosis is treated as frozen input. This module never re-judges the
claim; it renders the feedback prompt, calls an OpenAI-compatible chat
endpoint, validates the resulting natural-language text, and falls back to a
deterministic text when the call or the validation fails.

Public API:
    generate_feedback_v3(claim, diagnosis, knowledge_card, ...) -> FeedbackResult

Required environment variables for a real call:
    LLM_API_KEY
    LLM_BASE_URL   (default: https://api.deepseek.com/v1)
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
DEFAULT_PROMPT_PATH = APP_DIR / "prompts" / "feedback_prompt.md"
DEFAULT_CARD_PATH = APP_DIR.parent / "v2" / "agenda-setting.json"

VERDICTS = ("对", "部分对", "错", "依据不足")
COVERAGE_LEVELS = (
    "knowledge_backed",
    "ai_judged",
    "contradicted",
    "undetermined",
)
PASS_END = "这一题通过。"
REANSWER_END = "请根据以上要点重新作答。"
OFFTOPIC_END = "请确认你要作答的概念，然后重新作答。"
AI_REFERENCE_MARK = "这是 AI 提供的参考表述，未核验。"

FORBIDDEN_TERMS = (
    "card_ref",
    "coverage_level",
    "verdict",
    "error_type",
    "evidence_gap",
    "covered_key_elements",
    "missing_key_elements",
    "key_elements_required",
    "concept_development",
    "classic_definition_comparison",
    "deviation_note",
    "ai_generated",
    "unverified",
    "knowledge_backed",
    "ai_judged",
    "contradicted",
    "undetermined",
    "claim_span",
    "uncovered_dimensions",
    "adjacent_concepts",
    "necessary_boundary",
    "common_misreadings",
    "core_definition",
)

FORBIDDEN_PHRASES = (
    "你想怎么改",
    "你可以先告诉我",
    "下一步可以",
    "最关键的修改",
    "建议你改成",
    "你可以尝试这样改",
    "你觉得呢",
    "拆开看",
    "从句子结构看",
    "问题正出在",
    "该判断为",
    "整体判错",
)

PATH_PATTERN = re.compile(
    r"(?:checkpoints|core_definition|necessary_boundary|common_misreadings|"
    r"adjacent_concepts|uncovered_dimensions|key_elements_required|"
    r"concept_development|frameworks|disagreements|common_confusions)\s*\["
)


@dataclass
class FeedbackResult:
    text: str
    degraded: bool = False
    validation_errors: list[str] = field(default_factory=list)
    returned_model: str | None = None
    finish_reason: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: int = 0
    error: str | None = None
    raw_text: str | None = None
    attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "degraded": self.degraded,
            "validation_errors": list(self.validation_errors),
            "returned_model": self.returned_model,
            "finish_reason": self.finish_reason,
            "usage": dict(self.usage or {}),
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
            "raw_text": self.raw_text,
            "attempts": self.attempts,
        }


def load_json(source: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(source, dict):
        return source
    path = Path(source)
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层不是对象: {path}")
    return value


def strip_diagnosis(diagnosis: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with the fields the feedback prompt must not see."""
    clean = copy.deepcopy(diagnosis)
    clean.pop("summary", None)
    points = clean.get("points")
    if isinstance(points, list):
        for point in points:
            if isinstance(point, dict):
                point.pop("correction", None)
    return clean


def render_feedback_prompt(
    template: str,
    diagnosis: dict[str, Any],
    knowledge_card: dict[str, Any],
) -> str:
    if "{{DIAGNOSIS_JSON}}" not in template:
        raise ValueError("反馈 prompt 缺少 {{DIAGNOSIS_JSON}} 占位符")
    if "{{KNOWLEDGE_CARD_JSON}}" not in template:
        raise ValueError("反馈 prompt 缺少 {{KNOWLEDGE_CARD_JSON}} 占位符")
    clean = strip_diagnosis(diagnosis)
    diagnosis_json = json.dumps(clean, ensure_ascii=False, indent=2)
    card_json = json.dumps(knowledge_card, ensure_ascii=False, indent=2)
    return template.replace("{{DIAGNOSIS_JSON}}", diagnosis_json).replace(
        "{{KNOWLEDGE_CARD_JSON}}", card_json
    )


def _required_map(knowledge_card: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in knowledge_card.get("key_elements_required") or []:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            result[item["id"]] = item
    return result


def _concept_development(knowledge_card: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in knowledge_card.get("concept_development") or []
        if isinstance(item, dict)
    ]


def _flatten_elements(
    diagnosis: dict[str, Any],
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    covered_order: list[str] = []
    missing_by_id: dict[str, dict[str, Any]] = {}
    for point in diagnosis.get("points") or []:
        if not isinstance(point, dict):
            continue
        for element_id in point.get("covered_key_elements") or []:
            if isinstance(element_id, str) and element_id not in covered_order:
                covered_order.append(element_id)
        for item in point.get("missing_key_elements") or []:
            if not isinstance(item, dict):
                continue
            element_id = item.get("id")
            if isinstance(element_id, str) and element_id not in missing_by_id:
                missing_by_id[element_id] = item
    return covered_order, missing_by_id


def has_element_coverage(diagnosis: dict[str, Any]) -> bool:
    """Whether every point carries the two key-element arrays.

    The v3 diagnosis schema requires both arrays even when they are empty.
    An older diagnosis prompt can return the eight core fields without them;
    the feedback layer must not silently treat that as full coverage.
    """
    points = [p for p in diagnosis.get("points") or [] if isinstance(p, dict)]
    return bool(points) and all(
        isinstance(point.get("covered_key_elements"), list)
        and isinstance(point.get("missing_key_elements"), list)
        for point in points
    )


def _is_out_of_scope_point(point: dict[str, Any]) -> bool:
    if point.get("coverage_level") != "ai_judged":
        return False
    if point.get("covered_key_elements") or point.get("missing_key_elements"):
        return False
    comparison = str(point.get("classic_definition_comparison") or "")
    refs = point.get("card_ref") or []
    return "不在范围内" in comparison or any(
        isinstance(ref, str) and "core_definition[" in ref for ref in refs
    )


def _points_all_verdict(
    diagnosis: dict[str, Any], expected: str = "对"
) -> bool:
    points = [p for p in diagnosis.get("points") or [] if isinstance(p, dict)]
    return bool(points) and all(p.get("verdict") == expected for p in points)


def _has_ai_reference_mark(text: str) -> bool:
    """Accept the exact marker or an equivalent dialogue-style declaration."""
    if AI_REFERENCE_MARK in text:
        return True
    return bool(
        re.search(
            r"AI[^。！？]{0,50}(?:生成|参考)[^。！？]{0,50}未核验|"
            r"未核验[^。！？]{0,50}AI",
            text,
        )
    )


def is_offtopic_diagnosis(diagnosis: dict[str, Any]) -> bool:
    """Whether the frozen diagnosis is the off-topic/concept-confusion branch."""
    top_gap = str(diagnosis.get("evidence_gap") or "").lstrip()
    top_subject = str(diagnosis.get("subject") or "")
    if top_gap.startswith("跑题：") or "跑题" in top_subject:
        return True
    for point in diagnosis.get("points") or []:
        if not isinstance(point, dict):
            continue
        gap = str(point.get("evidence_gap") or "").lstrip()
        subject = str(point.get("subject") or "")
        if gap.startswith("跑题：") or "跑题" in subject:
            return True
    return False


def repair_diagnosis_coverage(
    diagnosis: dict[str, Any],
    knowledge_card: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Make element accounting internally consistent before validation.

    The diagnosis model occasionally returns ``overall="对"`` while a required
    element is neither in ``covered_key_elements`` nor in
    ``missing_key_elements``.  Trusting ``overall`` would silently pass an
    uncovered element; rejecting the whole diagnosis would white-screen the
    feedback layer.  This conservative repair treats every unclassified
    required element as missing and downgrades ``overall`` accordingly.

    Returns a deep-copied diagnosis and a human-readable list of repairs.
    The function is idempotent and leaves off-topic / fully out-of-scope
    diagnoses untouched.
    """

    if not isinstance(diagnosis, dict) or is_offtopic_diagnosis(diagnosis):
        return diagnosis, []
    raw_points = diagnosis.get("points")
    if not isinstance(raw_points, list) or not raw_points:
        return diagnosis, []
    dict_points = [point for point in raw_points if isinstance(point, dict)]
    if not dict_points:
        return diagnosis, []

    required = _required_map(knowledge_card)
    if not required:
        return diagnosis, []
    if all(_is_out_of_scope_point(point) for point in dict_points):
        return diagnosis, []

    repaired = copy.deepcopy(diagnosis)
    points = [point for point in repaired.get("points") or [] if isinstance(point, dict)]
    repairs: list[str] = []

    covered_order, _ = _flatten_elements(repaired)
    covered = set(covered_order)

    for index, point in enumerate(points):
        missing = point.get("missing_key_elements")
        if not isinstance(missing, list):
            continue
        cleaned: list[Any] = []
        for item in missing:
            if not isinstance(item, dict):
                cleaned.append(item)
                continue
            element_id = item.get("id")
            if isinstance(element_id, str) and element_id in covered:
                repairs.append(f"points[{index}] 移除已覆盖要素 {element_id}")
                continue
            if isinstance(element_id, str) and element_id in required:
                expected = required[element_id].get("standard_statement")
                if item.get("standard_statement") != expected:
                    item = dict(item)
                    item["standard_statement"] = expected
                    repairs.append(f"points[{index}] 修正 {element_id} 标准表述")
            cleaned.append(item)
        point["missing_key_elements"] = cleaned

    _, missing_map = _flatten_elements(repaired)
    missing = set(missing_map)
    uncovered = [
        element_id
        for element_id in required
        if element_id not in covered and element_id not in missing
    ]
    if uncovered:
        target = points[-1]
        target_missing = target.get("missing_key_elements")
        if not isinstance(target_missing, list):
            target_missing = []
            target["missing_key_elements"] = target_missing
        for element_id in uncovered:
            target_missing.append(
                {
                    "id": element_id,
                    "standard_statement": required[element_id].get("standard_statement"),
                }
            )
            missing.add(element_id)
            repairs.append(f"补充未归类必需元素 {element_id}")

    if repaired.get("overall") == "对":
        if missing:
            repaired["overall"] = "部分对"
            repairs.append("overall 由“对”降为“部分对”（存在未覆盖要素）")
        elif not _points_all_verdict(repaired, "对"):
            repaired["overall"] = "部分对"
            repairs.append("overall 由“对”降为“部分对”（存在非“对”诊断点）")

    return repaired, repairs


def validate_diagnosis_input(
    claim: str,
    diagnosis: dict[str, Any],
    knowledge_card: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(diagnosis, dict):
        return ["diagnosis 必须是 JSON 对象"]
    if diagnosis.get("claim") != claim:
        errors.append("diagnosis.claim 与输入 claim 不一致")
    if not isinstance(diagnosis.get("overall"), str) or diagnosis.get(
        "overall"
    ) not in VERDICTS:
        errors.append("diagnosis.overall 不是允许的判断值")
    points = diagnosis.get("points")
    if not isinstance(points, list) or not points:
        return errors + ["diagnosis.points 必须是非空数组"]

    if is_offtopic_diagnosis(diagnosis):
        return errors

    required = _required_map(knowledge_card)
    all_points_out_of_scope = True
    for index, point in enumerate(points):
        prefix = f"points[{index}]"
        if not isinstance(point, dict):
            errors.append(f"{prefix} 必须是对象")
            all_points_out_of_scope = False
            continue
        span = point.get("claim_span")
        if not isinstance(span, str) or not span.strip():
            errors.append(f"{prefix}.claim_span 缺失或为空")
        elif span not in claim:
            errors.append(f"{prefix}.claim_span 不是 claim 的连续原文片段")
        if point.get("coverage_level") not in COVERAGE_LEVELS:
            errors.append(f"{prefix}.coverage_level 不是四档之一")
        if point.get("verdict") not in VERDICTS:
            errors.append(f"{prefix}.verdict 不是允许的判断值")
        if not _is_out_of_scope_point(point):
            all_points_out_of_scope = False

        covered = point.get("covered_key_elements")
        missing = point.get("missing_key_elements")
        if not isinstance(covered, list):
            errors.append(f"{prefix}.covered_key_elements 缺失或不是数组")
            covered = []
        if not isinstance(missing, list):
            errors.append(f"{prefix}.missing_key_elements 缺失或不是数组")
            missing = []

        seen_covered: set[str] = set()
        for element_id in covered:
            if not isinstance(element_id, str):
                errors.append(f"{prefix}.covered_key_elements 含非字符串项")
                continue
            if element_id in seen_covered:
                errors.append(f"{prefix}.covered_key_elements 含重复 id {element_id}")
            seen_covered.add(element_id)
            if element_id not in required:
                errors.append(f"{prefix}.covered_key_elements 含未知 id {element_id}")

        seen_missing: set[str] = set()
        for item in missing:
            if not isinstance(item, dict):
                errors.append(f"{prefix}.missing_key_elements 含非对象项")
                continue
            element_id = item.get("id")
            if not isinstance(element_id, str) or element_id not in required:
                errors.append(f"{prefix}.missing_key_elements 含未知 id {element_id}")
                continue
            if element_id in seen_missing:
                errors.append(f"{prefix}.missing_key_elements 含重复 id {element_id}")
            seen_missing.add(element_id)
            expected = required[element_id].get("standard_statement")
            if item.get("standard_statement") != expected:
                errors.append(
                    f"{prefix}.missing_key_elements[{element_id}]."
                    "standard_statement 未逐字取自知识卡"
                )

    covered_all, missing_all = _flatten_elements(diagnosis)
    if diagnosis.get("overall") == "对":
        if not _points_all_verdict(diagnosis, "对"):
            errors.append("overall=对 但存在非“对”的诊断点")
        if missing_all:
            errors.append("overall=对 但 missing_key_elements 非空")
        if not all_points_out_of_scope:
            uncovered = set(required) - set(covered_all)
            if uncovered:
                errors.append(
                    "overall=对 但必需要素未全部覆盖: "
                    + ", ".join(sorted(uncovered))
                )
    return errors


def _judgment_present(text: str, overall: str) -> bool:
    if overall == "部分对":
        return "部分对" in text
    if overall == "依据不足":
        return "依据不足" in text
    if overall == "错":
        return bool(
            re.search(r"(整体判断|整体结果|判断结果)[^。！？]{0,20}错", text)
            or re.search(r"(回答|说法|判断)[^。！？]{0,12}错", text)
        )
    if overall == "对":
        return bool(
            re.search(r"(整体判断|整体结果|判断结果)[^。！？]{0,20}对", text)
            or "这一题通过" in text
            or "答对了" in text
        )
    return False


def _human_text_ok(text: str, knowledge_card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lowered = text.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            errors.append(f"反馈出现内部字段或枚举: {term}")
    if PATH_PATTERN.search(text):
        errors.append("反馈出现知识卡字段路径")
    if re.search(r"\bK[1-9]\b", text):
        errors.append("反馈出现内部要素 id")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            errors.append(f"反馈出现禁止的追问/评注表达: {phrase}")
    if "{{" in text or "}}" in text:
        errors.append("反馈残留模板占位符")
    if re.search(r"(^|\n)\s*(card_ref|coverage_level|verdict|error_type)\s*[:：]", lowered):
        errors.append("反馈出现字段名行")
    return errors


def validate_feedback_text(
    text: str,
    diagnosis: dict[str, Any],
    knowledge_card: dict[str, Any],
) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        return ["反馈文本为空"]
    text = text.strip()
    errors: list[str] = []
    errors.extend(_human_text_ok(text, knowledge_card))

    if is_offtopic_diagnosis(diagnosis):
        stripped = text.rstrip()
        if not stripped.endswith(OFFTOPIC_END):
            errors.append(f"跑题反馈最后一句不是“{OFFTOPIC_END}”")
        if "混淆" not in stripped and "是不是" not in stripped:
            errors.append("跑题反馈没有指出概念混淆")
        if PASS_END in stripped or REANSWER_END in stripped:
            errors.append("跑题反馈混入了常规通过/重答结尾")
        return errors

    overall = diagnosis.get("overall")
    if overall not in VERDICTS:
        errors.append("diagnosis.overall 非法，无法校验反馈")
        return errors
    if not _judgment_present(text, overall):
        errors.append("反馈缺少明确的整体判断")

    required = _required_map(knowledge_card)
    points = [p for p in diagnosis.get("points") or [] if isinstance(p, dict)]
    covered, missing = _flatten_elements(diagnosis)

    if covered:
        covered_names = [
            required[element_id]["element"]
            for element_id in covered
            if element_id in required
            and isinstance(required[element_id].get("element"), str)
        ]
        if not any(name in text for name in covered_names) and not any(
            word in text for word in ("答到了", "覆盖", "说到")
        ):
            errors.append("反馈没有说明用户答到了什么")
    elif not any(
        phrase in text
        for phrase in ("没有答到", "未答到", "没有覆盖", "没答到")
    ):
        errors.append("反馈没有说明用户没有答到必需要素")

    if missing:
        for element_id, item in missing.items():
            statement = item.get("standard_statement")
            if not isinstance(statement, str) or statement not in text:
                errors.append(
                    f"反馈未逐字展示遗漏要素 {element_id} 的 standard_statement"
                )
        if not any(word in text for word in ("漏", "缺", "未覆盖")):
            errors.append("反馈没有说明用户漏掉了什么")

    stage_names = [
        str(item.get("stage"))
        for item in _concept_development(knowledge_card)
        if item.get("stage")
    ]
    if not any(name in text for name in stage_names) and not re.search(
        r"第一层|第二层|网络议程设置", text
    ):
        errors.append("反馈没有展示概念发展脉络")

    for index, point in enumerate(points):
        span = point.get("claim_span")
        if isinstance(span, str) and span.strip() and span not in text:
            errors.append(f"反馈未逐字包含 points[{index}].claim_span")

    if any(p.get("coverage_level") == "ai_judged" for p in points):
        if not _has_ai_reference_mark(text):
            errors.append("反馈缺少 AI 生成/未核验声明")

    _, missing_all = _flatten_elements(diagnosis)
    covered_all, _ = _flatten_elements(diagnosis)
    all_points_out_of_scope = bool(points) and all(
        _is_out_of_scope_point(p) for p in points
    )
    effective_pass = (
        overall == "对"
        and not missing_all
        and not all_points_out_of_scope
        and _points_all_verdict(diagnosis, "对")
        and (
            (required and set(required) <= set(covered_all))
            or not required
        )
    )
    stripped = text.rstrip()
    if effective_pass:
        if PASS_END not in stripped:
            errors.append("全对反馈缺少“这一题通过”")
        if not stripped.endswith(PASS_END):
            errors.append("全对反馈没有以“这一题通过。”结束")
        if REANSWER_END in stripped:
            errors.append("全对反馈仍然要求重新作答")
    else:
        if not stripped.endswith(REANSWER_END):
            errors.append("未通过反馈最后一句不是“请根据以上要点重新作答。”")
        if PASS_END in stripped:
            errors.append("未通过反馈出现了“这一题通过”")
    return errors


def _claim_span_error_indexes(errors: list[str]) -> list[int]:
    indexes: list[int] = []
    for error in errors:
        match = re.fullmatch(r"反馈未逐字包含 points\[(\d+)\]\.claim_span", error)
        if not match:
            continue
        index = int(match.group(1))
        if index not in indexes:
            indexes.append(index)
    return indexes


def _build_claim_span_retry_prompt(
    base_prompt: str,
    diagnosis: dict[str, Any],
    errors: list[str],
) -> str | None:
    indexes = _claim_span_error_indexes(errors)
    if not indexes:
        return None
    points = diagnosis.get("points") or []
    spans: list[str] = []
    for index in indexes:
        if 0 <= index < len(points) and isinstance(points[index], dict):
            span = points[index].get("claim_span")
            if isinstance(span, str) and span.strip():
                spans.append(span)
    if not spans:
        return None
    lines = [
        "## 上一次输出未通过逐字引用校验",
        "",
        "请重写一份完整的反馈正文。保留已经正确的整体判断、要素说明和概念脉络，并确保下列用户原文片段在正文中逐字出现一次：引号内保留原句的第一人称“我”、语序和标点，不得改成第二人称“你”，不得概括、压缩或删改；第二人称只用在引号外。",
        "",
    ]
    lines.extend(f"- “{span}”" for span in spans)
    lines.extend(
        [
            "",
            "不要提到这次修正、校验过程或任何内部字段；直接输出修正后的完整反馈正文。",
        ]
    )
    return base_prompt + "\n\n" + "\n".join(lines)


def _repair_missing_claim_spans(
    text: str,
    diagnosis: dict[str, Any],
) -> tuple[str, list[str]]:
    """Quote claim spans the model omitted without weakening validation.

    Long claims can produce more diagnostic points than the prompt's nominal
    1-5 limit. A retry can still omit one or two literal spans even when the
    rest of the feedback is usable. This deterministic repair only quotes the
    user's original fragments in a short closing check; it never re-judges the
    claim or invents a new conclusion.
    """
    if is_offtopic_diagnosis(diagnosis):
        return text, []

    points = [p for p in diagnosis.get("points") or [] if isinstance(p, dict)]
    missing: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for point in points:
        span = point.get("claim_span")
        if (
            not isinstance(span, str)
            or not span.strip()
            or span in text
            or span in seen
        ):
            continue
        verdict = point.get("verdict")
        missing.append((span, verdict if isinstance(verdict, str) else None))
        seen.add(span)

    missing_ai_mark = any(
        isinstance(point, dict)
        and point.get("coverage_level") == "ai_judged"
        for point in points
    ) and not _has_ai_reference_mark(text)

    if not missing and not missing_ai_mark:
        return text, []

    clauses: list[str] = []
    for span, verdict in missing:
        if verdict in VERDICTS:
            clauses.append(f"你写到“{span}”，这一处判断为{verdict}")
        else:
            clauses.append(f"你写到“{span}”")
    block_parts: list[str] = []
    if clauses:
        block_parts.append(
            "另外，还有几处你的原话需要逐字核对：" + "；".join(clauses) + "。"
        )
    if missing_ai_mark:
        block_parts.append(
            "其中涉及类比判断的部分，是 AI 提供的参考表述，未核验。"
        )
    block = "".join(block_parts)

    stripped = text.rstrip()
    for ending in (REANSWER_END, PASS_END, OFFTOPIC_END):
        if stripped.endswith(ending):
            prefix = stripped[: -len(ending)].rstrip()
            if prefix:
                repaired = f"{prefix}\n\n{block}\n\n{ending}"
            else:
                repaired = f"{block}\n\n{ending}"
            return repaired, [span for span, _ in missing]
    return f"{stripped}\n\n{block}", [span for span, _ in missing]


def _merge_usage(total: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(total or {})
    for key, value in (extra or {}).items():
        current = merged.get(key)
        if isinstance(current, int) and isinstance(value, int):
            merged[key] = current + value
        else:
            merged[key] = value
    return merged


def _concept_sentence(knowledge_card: dict[str, Any]) -> str:
    development = _concept_development(knowledge_card)
    if not development:
        return ""
    pieces: list[str] = []
    for item in development:
        stage = item.get("stage")
        contribution = item.get("contribution")
        period = item.get("period")
        if not stage or not contribution:
            continue
        prefix = str(stage)
        if period:
            prefix += f"（{period}）"
        pieces.append(f"{prefix}：{contribution}")
    if not pieces:
        return ""
    return "这个概念的发展脉络是：" + "；".join(pieces) + "。"


def _fallback_text(
    claim: str,
    diagnosis: dict[str, Any],
    knowledge_card: dict[str, Any],
) -> str:
    if is_offtopic_diagnosis(diagnosis):
        concept = str(diagnosis.get("concept") or "当前概念")
        return (
            f"你这次回答的内容不属于要考察的{concept}，看起来是概念混淆了。\n\n"
            "当前概念问的是媒体如何影响公众对议题重要性的判断，而不是另一个传播机制。\n\n"
            f"{OFFTOPIC_END}"
        )

    if not has_element_coverage(diagnosis):
        overall = diagnosis.get("overall")
        if overall not in VERDICTS:
            overall = "依据不足"
        return (
            f"这次反馈无法完成要素核对：诊断没有提供要素覆盖信息（原始判断为{overall}）。"
            "\n\n"
            "我不能据此判定为通过，也不会把缺少的信息补成你的答案。"
            "\n\n"
            "请根据以上要点重新作答。"
        )

    required = _required_map(knowledge_card)
    covered, missing = _flatten_elements(diagnosis)
    points = [p for p in diagnosis.get("points") or [] if isinstance(p, dict)]
    all_points_out_of_scope = bool(points) and all(
        _is_out_of_scope_point(p) for p in points
    )
    overall = diagnosis.get("overall")
    if overall not in VERDICTS:
        overall = "依据不足"
    points_ok = _points_all_verdict(diagnosis, "对")
    effective_pass = (
        overall == "对"
        and points_ok
        and not missing
        and not all_points_out_of_scope
        and (
            (required and set(required) <= set(covered))
            or not required
        )
    )
    if overall == "对" and (missing or not points_ok):
        overall = "部分对"

    if all_points_out_of_scope:
        parts = [
            f"这次整体判断为{overall}，但你这句话讨论的内容不在议程设置的概念范围内，不能算覆盖了议程设置的必需要素。"
        ]
        if any(p.get("coverage_level") == "ai_judged" for p in points):
            parts.append(AI_REFERENCE_MARK)
        parts.append(REANSWER_END)
        return "\n\n".join(parts)

    if effective_pass:
        names = [
            required[element_id]["element"]
            for element_id in covered
            if element_id in required and required[element_id].get("element")
        ]
        text = "这次整体判断为对，你答到了全部必需要素。"
        if names:
            text = "这次整体判断为对，你答到了全部必需要素："
            text += "、".join(str(name) for name in names) + "。"
        development = _concept_sentence(knowledge_card)
        parts = [text]
        if development:
            parts.append(development)
        parts.append(PASS_END)
        return "\n\n".join(parts)

    parts = [f"这次整体判断为{overall}。"]
    if covered:
        names = [
            str(required[element_id].get("element"))
            for element_id in covered
            if element_id in required and required[element_id].get("element")
        ]
        if names:
            parts.append("你答到了：" + "、".join(names) + "。")
        else:
            parts.append("你答到了部分必需要素。")
    else:
        parts.append("这次没有答到必需要素。")

    if missing:
        lines: list[str] = []
        for element_id, item in missing.items():
            name = (
                required.get(element_id, {}).get("element")
                or "一个必需要素"
            )
            statement = item.get("standard_statement")
            if not isinstance(statement, str) or not statement:
                statement = required.get(element_id, {}).get(
                    "standard_statement", ""
                )
            if statement:
                lines.append(f"{name}：标准表述是：{statement}")
            else:
                lines.append(f"{name}：诊断没有提供标准表述。")
        parts.append("你漏掉的是：" + " ".join(lines))
    else:
        parts.append("诊断没有列出可核对的必需要素漏项。")

    development = _concept_sentence(knowledge_card)
    if development:
        parts.append(development)
    parts.append(REANSWER_END)
    return "\n\n".join(parts)


def _endpoint(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        base = "https://api.deepseek.com/v1"
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def _chat_completion(
    prompt: str,
    *,
    model: str,
    max_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("LLM_API_KEY 未设置")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "请严格按上述规则，生成用户可读的反馈正文。",
            },
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        _endpoint(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise RuntimeError(
            f"LLM 请求超时（{timeout} 秒），已改用兜底反馈。"
        ) from exc
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
            raise RuntimeError(
                f"LLM 请求超时（{timeout} 秒），已改用兜底反馈。"
            ) from exc
        raise RuntimeError(f"LLM 连接失败: {exc}") from exc
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("LLM 返回中没有 choices")
    choice = choices[0] or {}
    content = (choice.get("message") or {}).get("content") or ""
    finish_reason = choice.get("finish_reason")
    if str(finish_reason or "").lower() in {"length", "max_tokens"}:
        raise RuntimeError(
            "反馈输出被截断（finish_reason=length），已改用兜底反馈。"
        )
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM 返回内容为空")
    return {
        "content": content.strip(),
        "returned_model": body.get("model"),
        "finish_reason": finish_reason,
        "usage": body.get("usage") or {},
    }


def _log_result(result: FeedbackResult, model: str, log: bool) -> None:
    if not log:
        return
    usage = result.usage or {}
    payload = {
        "event": "feedback_v3",
        "model_requested": model,
        "returned_model": result.returned_model,
        "finish_reason": result.finish_reason,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "elapsed_ms": result.elapsed_ms,
        "attempts": result.attempts,
        "degraded": result.degraded,
        "validation_errors": result.validation_errors,
        "error": result.error,
    }
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)


def generate_feedback_v3(
    claim: str,
    diagnosis: dict[str, Any] | str | Path,
    knowledge_card: dict[str, Any] | str | Path,
    *,
    prompt_path: str | Path = DEFAULT_PROMPT_PATH,
    model: str | None = None,
    max_tokens: int | None = None,
    timeout: int = 120,
    log: bool = True,
) -> FeedbackResult:
    """Generate validated feedback; never raise on model or validation failure."""
    started = time.perf_counter()
    requested_model = model or os.environ.get("LLM_MODEL", "deepseek-chat")
    token_limit = max_tokens or int(os.environ.get("LLM_MAX_TOKENS", "4000"))
    result = FeedbackResult(text="")
    diagnosis_obj: dict[str, Any] = {}
    card_obj: dict[str, Any] = {}
    attempts = 0

    try:
        diagnosis_obj = load_json(diagnosis)
        card_obj = load_json(knowledge_card)
        diagnosis_obj, coverage_repairs = repair_diagnosis_coverage(
            diagnosis_obj, card_obj
        )
        if coverage_repairs and log:
            print(
                "[feedback_v3] diagnosis coverage repaired: "
                + "；".join(coverage_repairs),
                file=sys.stderr,
            )
        input_errors = validate_diagnosis_input(claim, diagnosis_obj, card_obj)
        if input_errors:
            result.validation_errors = list(input_errors)
            raise ValueError("；".join(input_errors))
        template = Path(prompt_path).read_text(encoding="utf-8")
        prompt = render_feedback_prompt(template, diagnosis_obj, card_obj)
        attempts += 1
        response = _chat_completion(
            prompt,
            model=requested_model,
            max_tokens=token_limit,
            timeout=timeout,
        )
        usage = dict(response.get("usage") or {})
        content = response["content"]
        validation_errors = validate_feedback_text(content, diagnosis_obj, card_obj)
        if validation_errors:
            retry_prompt = _build_claim_span_retry_prompt(
                prompt, diagnosis_obj, validation_errors
            )
            if retry_prompt:
                attempts += 1
                response = _chat_completion(
                    retry_prompt,
                    model=requested_model,
                    max_tokens=token_limit,
                    timeout=timeout,
                )
                usage = _merge_usage(usage, response.get("usage") or {})
                content = response["content"]
                validation_errors = validate_feedback_text(
                    content, diagnosis_obj, card_obj
                )
        raw_content = content
        if _claim_span_error_indexes(validation_errors) or (
            any(
                isinstance(point, dict)
                and point.get("coverage_level") == "ai_judged"
                for point in diagnosis_obj.get("points") or []
            )
            and not _has_ai_reference_mark(content)
        ):
            before_repair = content
            content, repaired_spans = _repair_missing_claim_spans(
                content, diagnosis_obj
            )
            if content != before_repair:
                validation_errors = validate_feedback_text(
                    content, diagnosis_obj, card_obj
                )
                if log and repaired_spans:
                    print(
                        "[feedback_v3] repaired missing claim spans: "
                        + "；".join(repaired_spans),
                        file=sys.stderr,
                    )
        result.raw_text = raw_content
        result.returned_model = response.get("returned_model")
        result.finish_reason = response.get("finish_reason")
        result.usage = usage
        result.attempts = attempts
        result.validation_errors = list(validation_errors)
        if validation_errors:
            raise ValueError("反馈校验失败：" + "；".join(validation_errors))
        result.text = content
        result.degraded = False
        result.validation_errors = []
        result.elapsed_ms = round((time.perf_counter() - started) * 1000)
        _log_result(result, requested_model, log)
        return result
    except Exception as exc:
        if not diagnosis_obj:
            diagnosis_obj = diagnosis if isinstance(diagnosis, dict) else {}
        if not card_obj:
            card_obj = knowledge_card if isinstance(knowledge_card, dict) else {}
        result.text = _fallback_text(claim, diagnosis_obj, card_obj)
        result.degraded = True
        result.error = f"{type(exc).__name__}: {exc}"
        result.attempts = attempts
        result.elapsed_ms = round((time.perf_counter() - started) * 1000)
        _log_result(result, requested_model, log)
        return result


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Generate agenda-setting v3 learning-loop feedback"
    )
    parser.add_argument("--claim", required=True)
    parser.add_argument("--diagnosis", required=True)
    parser.add_argument("--card", default=str(DEFAULT_CARD_PATH))
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument(
        "--model", default=os.environ.get("LLM_MODEL", "deepseek-chat")
    )
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--meta",
        action="store_true",
        help="print the full result object to stdout as JSON",
    )
    args = parser.parse_args()

    result = generate_feedback_v3(
        args.claim,
        args.diagnosis,
        args.card,
        prompt_path=args.prompt,
        model=args.model,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
    )
    if args.meta:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
