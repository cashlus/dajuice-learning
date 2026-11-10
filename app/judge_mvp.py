#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""liberty v2 框架归属判定 MVP：只输出三型结构化 JSON，不做反馈层。"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

RESULT_TYPES = ("single_framework", "ambiguous_between_frameworks", "no_coverage")

ALLOWED_KEYS = {
    "single_framework": {"result_type", "framework", "confusion_hit", "evidence_refs", "next_question"},
    "ambiguous_between_frameworks": {"result_type", "candidates", "confusion_hit", "evidence_refs", "next_question"},
    "no_coverage": {"result_type", "reason", "evidence_refs"},
}

SYSTEM_PROMPT = "你是严格的框架归属分类器。只输出一个 JSON 对象，不输出解释或 Markdown。"


def load_concept(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        concept = json.load(handle)
    for key in ("concept", "core_question", "frameworks", "common_confusions"):
        if key not in concept:
            raise ValueError(f"概念 JSON 缺少字段: {key}")
    return concept


def allowed_refs(concept: dict) -> list[str]:
    refs = ["core_question"]
    for i, framework in enumerate(concept["frameworks"]):
        refs.append(f"frameworks[{i}].answers")
        for j in range(len(framework.get("key_spans", []))):
            refs.append(f"frameworks[{i}].key_spans[{j}]")
        for j in range(len(framework.get("misreadings", []))):
            refs.append(f"frameworks[{i}].misreadings[{j}]")
    for i, confusion in enumerate(concept["common_confusions"]):
        refs.append(f"common_confusions[{i}].confusion")
        refs.append(f"common_confusions[{i}].what_is_confused")
        refs.append(f"common_confusions[{i}].diagnosis")
        for j in range(len(confusion.get("key_spans", []))):
            refs.append(f"common_confusions[{i}].key_spans[{j}]")
    return refs


def compact_concept(concept: dict) -> dict:
    return {
        "concept": concept["concept"],
        "core_question": concept["core_question"],
        "frameworks": [
            {
                "index": i,
                "name": framework["name"],
                "answers": framework["answers"],
                "key_spans": [
                    {"index": j, "text": span["text"], "source": span["source"]}
                    for j, span in enumerate(framework.get("key_spans", []))
                ],
                "misreadings": framework.get("misreadings", []),
            }
            for i, framework in enumerate(concept["frameworks"])
        ],
        "common_confusions": [
            {
                "index": i,
                "confusion": confusion["confusion"],
                "user_patterns": confusion.get("user_patterns", []),
                "what_is_confused": confusion["what_is_confused"],
                "diagnosis": confusion["diagnosis"],
                "trigger_condition": confusion.get("trigger_condition", ""),
                "key_spans": confusion.get("key_spans", []),
            }
            for i, confusion in enumerate(concept["common_confusions"])
        ],
    }


GUARD_PATTERNS = (
    "做自己想做的事",
    "做自己想做的",
    "想做什么就做什么",
    "想干什么就干什么",
)


def normalize_claim(text: str) -> str:
    return re.sub(r"[\s\u3000，。！？、；：,.!?;:\"'“”‘’（）()【】\[\]—\-]+", "", text or "")


def extract_confusion_question(confusion: dict) -> str:
    diagnosis = str(confusion.get("diagnosis", ""))
    marker = "再追问一句："
    if marker in diagnosis:
        tail = diagnosis.split(marker, 1)[1]
        cut = tail.find("——")
        if cut >= 0:
            tail = tail[:cut]
        tail = tail.strip()
        if tail:
            return tail
    questions = re.findall(r"[^。！？]*？", diagnosis)
    if questions:
        return questions[-1].strip()
    return diagnosis[:80].strip()


def deterministic_guard(claim: str, concept: dict, llm_output: dict) -> tuple[dict, bool]:
    """LLM 判定之后纠正第三问红线；返回 (公开输出, 是否发生纠正)。

    只在 LLM 已输出 single_framework 且 framework 为积极自由时纠正；
    框架与混淆均按名称/文本匹配，不依赖数组下标。
    """
    if not isinstance(llm_output, dict):
        raise TypeError("llm_output 必须是 dict")
    if concept.get("concept") != "liberty":
        return llm_output, False

    normalized = normalize_claim(claim)
    if not any(normalize_claim(pattern) in normalized for pattern in GUARD_PATTERNS):
        return llm_output, False

    frameworks = concept.get("frameworks") or []
    confusions = concept.get("common_confusions") or []
    negative = next((f for f in frameworks if "消极自由" in f.get("name", "")), None)
    positive = next((f for f in frameworks if "积极自由" in f.get("name", "")), None)
    confusion = next(
        (c for c in confusions if "做自己想做的事" in c.get("confusion", "")),
        None,
    )
    if negative is None or positive is None or confusion is None:
        return llm_output, False

    if llm_output.get("result_type") != "single_framework":
        return llm_output, False
    if llm_output.get("framework") != positive["name"]:
        return llm_output, False

    negative_index = frameworks.index(negative)
    positive_index = frameworks.index(positive)
    confusion_index = confusions.index(confusion)
    evidence = [
        f"common_confusions[{confusion_index}].diagnosis",
        f"frameworks[{negative_index}].answers",
        f"frameworks[{positive_index}].answers",
    ]
    if confusion.get("key_spans"):
        evidence.insert(1, f"common_confusions[{confusion_index}].key_spans[0]")

    corrected = {
        "result_type": "ambiguous_between_frameworks",
        "candidates": [negative["name"], positive["name"]],
        "confusion_hit": confusion["confusion"],
        "evidence_refs": evidence,
        "next_question": extract_confusion_question(confusion),
    }
    return corrected, True


def build_prompt(concept: dict, claim: str) -> str:
    refs = "\n".join(f"- {ref}" for ref in allowed_refs(concept))
    payload = json.dumps(compact_concept(concept), ensure_ascii=False, indent=2)
    template = """你是「liberty（自由）」概念知识库的框架归属分类器。你只做归属，不做反馈。

【唯一依据】
只能使用下面给出的 CONCEPT JSON。禁止引入任何外部哲学知识，禁止补充 JSON 里没有的框架。

【输出格式】
只输出一个 JSON 对象，不要 Markdown 代码块，不要解释，不要任何前后缀。
result_type 只能是三型之一，字段集合必须与该型完全一致（不能多字段，不能少字段）：

A. 单一框架
{"result_type": "single_framework", "framework": "<frameworks[].name 原文>", "confusion_hit": null 或 "<common_confusions[].confusion 原文>", "evidence_refs": ["<JSON 字段路径>"], "next_question": "<一句追问>"}
- A 型 evidence_refs 必须至少包含一个 frameworks[i].misreadings[j] 或 common_confusions[k].diagnosis 路径；只引 answers 或 confusion 不满足 next_question 的可追溯要求。

B. 框架间歧义
{"result_type": "ambiguous_between_frameworks", "candidates": ["<框架A>", "<框架B>"], "confusion_hit": "<common_confusions[].confusion 原文>", "evidence_refs": ["<JSON 字段路径>"], "next_question": "<一句区分性追问>"}

C. 无覆盖
{"result_type": "no_coverage", "reason": "<缺哪个框架/哪类回答>", "evidence_refs": []}

【判定顺序】
【B 型前置检查】判 B 型前，先检查 claim 是否同时包含两个框架各自能独立回答 core_question 的规范判据成分。若第二个成分只是第一个判据下的行动内容（例如“没人拦”之下的“想做什么”），不构成第二判据，判 A 型。B 型要求两个成分都能单独作为“自由是什么”的答案。
1. 若这句话同时可被两个框架的 answers 读出，且 common_confusions 中有一条正是为这种跨框架歧义而设 → B。candidates 写这两个框架名，confusion_hit 必须写那条混淆的原文。
2. 否则，若恰好一个框架的 answers 能覆盖 → A。
3. 否则 → C。C 的 evidence_refs 必须是空数组，不得编造证据。

【next_question 规则】
- A：必须改写自 evidence_refs 所引用的 frameworks[i].misreadings[j] 或 common_confusions[k].diagnosis 中的句子；不得引入 JSON 之外的信息。
- B：必须改写自 evidence_refs 所引用的 common_confusions[k].diagnosis，并且要能区分 candidates 里的两个框架。
- 只写一句，尽量不超过 60 个汉字。C 不输出 next_question。

【evidence_refs 白名单】
只能从下列路径中原样选择，不得自造：
__REFS__

【关键样例（必须遵守）】
claim = "自由是做自己想做的事"
→ result_type = "ambiguous_between_frameworks"
→ candidates = ["Berlin 式消极自由", "Berlin 式积极自由"]
→ confusion_hit = common_confusions 中「把「做自己想做的事」当成单一框架的定义（消极自由/积极自由混淆）」这一条
→ 不得输出 single_framework，尤其不得只输出「Berlin 式积极自由」

【CONCEPT JSON】
__CONCEPT__

【CLAIM】
__CLAIM__
"""
    return template.replace("__REFS__", refs).replace("__CONCEPT__", payload).replace("__CLAIM__", claim)


def chat(messages: list[dict], model: str, timeout: int = 120) -> str:
    base = os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not base or not key:
        raise RuntimeError("未设置 LLM_BASE_URL 或 LLM_API_KEY")
    if base.endswith("/chat/completions"):
        url = base
    elif base.endswith("/v1"):
        url = base + "/chat/completions"
    else:
        url = base + "/v1/chat/completions"

    body = {"model": model, "messages": messages, "temperature": 0, "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "4000"))}
    reasoning_effort = os.environ.get("LLM_REASONING_EFFORT", "").strip()
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM 连接失败: {exc.reason}") from exc

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"LLM 响应结构异常: {str(payload)[:500]}") from exc
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM 返回空内容")
    return content


def extract_json(text: str) -> dict:
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


def validate(output: dict, concept: dict, refs: list[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(output, dict):
        return ["输出不是 JSON 对象"]
    result_type = output.get("result_type")
    if result_type not in RESULT_TYPES:
        return [f"result_type 非法: {result_type!r}"]

    extra = set(output) - ALLOWED_KEYS[result_type]
    missing = ALLOWED_KEYS[result_type] - set(output)
    if extra:
        errors.append(f"多出字段: {sorted(extra)}")
    if missing:
        errors.append(f"缺少字段: {sorted(missing)}")

    evidence = output.get("evidence_refs")
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        errors.append("evidence_refs 必须是字符串数组")
        evidence = []
    if result_type in ("single_framework", "ambiguous_between_frameworks") and not evidence:
        errors.append("A/B 型 evidence_refs 不能为空")
    allowed = set(refs)
    for ref in evidence:
        if ref not in allowed:
            errors.append(f"evidence_ref 不在白名单: {ref}")

    framework_names = [framework["name"] for framework in concept["frameworks"]]
    confusion_names = [confusion["confusion"] for confusion in concept["common_confusions"]]

    if result_type == "single_framework":
        if output.get("framework") not in framework_names:
            errors.append("framework 必须是 frameworks[].name 的原文")
        confusion = output.get("confusion_hit")
        if confusion is not None and confusion not in confusion_names:
            errors.append("confusion_hit 必须是 common_confusions[].confusion 原文或 null")
        cited_confusions = set()
        for ref in evidence:
            match = re.fullmatch(r"common_confusions\[(\d+)\]\.(?:confusion|what_is_confused|diagnosis|key_spans\[\d+\])", ref)
            if match:
                cited_confusions.add(int(match.group(1)))
        if confusion is not None and confusion in confusion_names:
            index = confusion_names.index(confusion)
            if index not in cited_confusions:
                errors.append("confusion_hit 非空，但 evidence_refs 未引用该条 common_confusions")
        if cited_confusions and confusion is None:
            errors.append("evidence_refs 引用了 common_confusions，但 confusion_hit 为 null")
        question = output.get("next_question")
        if not isinstance(question, str) or not question.strip():
            errors.append("next_question 必须是非空字符串")
        traceable = any(
            re.fullmatch(r"frameworks\[\d+\]\.misreadings\[\d+\]", ref)
            or re.fullmatch(r"common_confusions\[\d+\]\.diagnosis", ref)
            for ref in evidence
        )
        if not traceable:
            errors.append("A 型的 next_question 缺少可追溯依据（misreadings 或 diagnosis）")

    elif result_type == "ambiguous_between_frameworks":
        candidates = output.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 2:
            errors.append("B 型 candidates 必须恰好 2 个框架")
        else:
            if len(set(candidates)) != len(candidates):
                errors.append("candidates 不得重复")
            for name in candidates:
                if name not in framework_names:
                    errors.append(f"candidate 不在 frameworks[].name 中: {name}")
        confusion = output.get("confusion_hit")
        if confusion not in confusion_names:
            errors.append("B 型 confusion_hit 必须是 common_confusions[].confusion 原文")
        else:
            index = confusion_names.index(confusion)
            if f"common_confusions[{index}].diagnosis" not in evidence:
                errors.append("B 型的 diagnosis 引用必须对应 confusion_hit 的同一条")
        question = output.get("next_question")
        if not isinstance(question, str) or not question.strip():
            errors.append("next_question 必须是非空字符串")

    else:
        reason = output.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append("reason 必须是非空字符串")
        if evidence:
            errors.append("C 型 evidence_refs 必须为空数组")

    return errors


def judge(claim: str, concept: dict, model: str, retries: int) -> tuple[dict, bool]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(concept, claim)},
    ]
    refs = allowed_refs(concept)
    last_error = "未知错误"

    for attempt in range(retries + 1):
        raw = chat(messages, model)
        try:
            output = extract_json(raw)
        except Exception as exc:
            last_error = f"JSON 解析失败: {exc}"
        else:
            errors = validate(output, concept, refs)
            if not errors:
                corrected, guard_correction = deterministic_guard(claim, concept, output)
                if guard_correction:
                    correction_errors = validate(corrected, concept, refs)
                    if correction_errors:
                        raise RuntimeError(
                            "guard 纠正结果未通过 schema 校验: " + "；".join(correction_errors)
                        )
                    return corrected, True
                return output, False
            last_error = "；".join(errors)

        if attempt < retries:
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"上一次输出不合法：{last_error}。请严格按三型 schema 重新输出一个 JSON 对象，不要解释。",
            })

    raise RuntimeError(f"判定失败（共尝试 {retries + 1} 次）：{last_error}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="liberty v2 框架归属判定 MVP")
    parser.add_argument("--claim", help="用户说法；省略则从 stdin 读取")
    parser.add_argument("--json", required=True, dest="json_path", help="liberty_v2.json 路径")
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL", "deepseek-v4-pro"))
    parser.add_argument("--retries", type=int, default=1, help="schema 校验失败后的重试次数")
    parser.add_argument("--prompt-only", action="store_true", help="只打印 prompt，不调用 LLM")
    args = parser.parse_args()

    claim = args.claim if args.claim is not None else sys.stdin.read()
    claim = claim.strip()
    if not claim:
        print("[judge_mvp] claim 为空", file=sys.stderr)
        return 2

    try:
        concept = load_concept(args.json_path)
    except Exception as exc:
        print(f"[judge_mvp] 读取概念 JSON 失败: {exc}", file=sys.stderr)
        return 2

    if args.prompt_only:
        print(build_prompt(concept, claim))
        return 0

    try:
        result, guard_correction = judge(claim, concept, args.model, max(args.retries, 0))
    except Exception as exc:
        print(f"[judge_mvp] {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if guard_correction:
        print(f"[guard] corrected claim={claim}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
