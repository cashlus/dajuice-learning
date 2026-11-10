"""Judge whether a claim is supported by the given source_spans, using an
OpenAI-compatible chat completion endpoint. Standard library only.

Required environment variables:
    LLM_API_KEY   - bearer token
    LLM_BASE_URL  - e.g. https://api.deepseek.com/v1
Optional:
    LLM_MODEL     - default deepseek-v4-pro
"""

import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KB = r"C:\Users\cashrus\Documents\Codex\.kb"
CONCEPT_PATH = os.path.join(KB, "concepts", "liberty.json")
CASES_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KB, "app", "test_cases.json")
RESULTS_PATH = (
    sys.argv[2] if len(sys.argv) > 2 else os.path.join(KB, "app", "results.jsonl")
)

VERDICTS = ("支持", "矛盾", "未被覆盖", "属于另一诠释")
ROLES = ("primary_def", "plain_def", "advanced_def")
SUPPORT_TYPES = ("direct", "synonym", "inference", "none")
LOGGER = logging.getLogger(__name__)
MAX_JUDGE_ATTEMPTS = 3

SYSTEM_PROMPT = (
    "你是一个严格的知识溯源判定器。你只能依据用户给出的 source_spans 判断，"
    "不得引入任何外部知识、常识或你对哲学史的记忆。\n"
    "按以下优先级依次适用判定规则：\n"
    "规则1（最高）：source_spans 中出现 claim 的直接用词，或存在学术上等价的同义表述，"
    "则 verdict=\"支持\"；直接词对应 support_type=\"direct\"，学术同义词对应 "
    "support_type=\"synonym\"；explanation 必须以“原文直述：”或“学术同义表述：”开头。\n"
    "规则2：原文没有直接词，但 claim 是原文概念的学术化具体化，或仅需一步且学术上无争议的推论，"
    "则 verdict=\"支持\"，support_type=\"inference\"；explanation 必须以“推论型支持：”开头，"
    "并写明推论依据（依据哪句原文、经过哪一步推到该 claim）。\n"
    "规则3：原文没有对应概念，且下方 stances 中也没有与该 claim 主题明确对应的传统，"
    "则 verdict=\"未被覆盖\"，support_type=\"none\"，evidence_quote 与 tradition_hint 均留空字符串。\n"
    "规则4：原文直接否定 claim，则 verdict=\"矛盾\"，support_type=\"none\"，"
    "evidence_quote 必须是原文中直接否定的那一句。\n"
    "规则5：claim 与 source_spans 既无直接支持、也无直接矛盾，但与下方 stances 中某条传统主题明确对应，"
    "则 verdict=\"属于另一诠释\"，support_type=\"none\"，evidence_quote 留空字符串，"
    "tradition_hint 必须逐字填入对应的那条 stance；若 stances 中也没有对应，才判\"未被覆盖\"，tradition_hint 留空字符串。\n"
    "tradition_hint 仅在 verdict=\"属于另一诠释\" 时非空，其余 verdict 一律留空字符串。\n"
    "只输出一个 JSON 对象，不要输出解释性文字、不要加代码块标记。"
)


def build_prompt(claim, spans, stances=None):
    blocks = []
    for i, s in enumerate(spans, 1):
        blocks.append(
            "[%d] role=%s segment_index=%s\n%s"
            % (i, s["role"], s["segment_index"], s["text"].strip())
        )
    stance_block = ""
    if stances:
        stance_block = (
            "\n\n可用传统立场（stances，仅用于生成 tradition_hint）：\n"
            + "\n".join("- " + s for s in stances)
        )
    return (
        "source_spans:\n\n"
        + "\n\n".join(blocks)
        + stance_block
        + "\n\n待判定断言：\n"
        + claim.strip()
        + "\n\n输出 JSON，字段与取值必须严格如下：\n"
        '{"verdict": "支持|矛盾|未被覆盖|属于另一诠释", '
        '"support_type": "direct|synonym|inference|none", '
        '"matched_role": "primary_def|plain_def|advanced_def", '
        '"evidence_quote": "source_spans 中逐字出现的原句片段", '
        '"explanation": "一句话说明", '
        '"tradition_hint": "属于另一诠释时逐字复制的对应 stance，其余情况空字符串"}\n'
        "要求：\n"
        "1. evidence_quote 必须是上面 source_spans 文本里连续出现的一段，不得改写、不得拼接；\n"
        "2. matched_role 必须是上面出现过的 role 之一；判“未被覆盖”或“属于另一诠释”时留空字符串；\n"
        "3. 判“未被覆盖”或“属于另一诠释”时 evidence_quote 留空字符串；\n"
        "4. support_type 与 verdict 必须匹配：支持→direct/synonym/inference，矛盾、未被覆盖或属于另一诠释→none；\n"
        "5. 推论型支持也必须给出最接近的原文依据句作为 evidence_quote；\n"
        "6. 中文回答，一句话，不超过 80 字；\n"
        "7. tradition_hint 必须逐字来自上面 stances 列表中的一条，不得改写、不得拼接；"
        "仅当 verdict=\"属于另一诠释\" 时必须非空，其余 verdict 一律留空字符串。"
    )


def _endpoint(base_url):
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start : end + 1])


def _normalize(s):
    return re.sub(r"\s+", " ", (s or "").replace("*", "")).strip()


def _request_judge(claim, source_spans, stances=None):
    payload = {
        "model": os.environ.get("LLM_MODEL", "deepseek-v4-pro"),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(claim, source_spans, stances)},
        ],
    }
    request = urllib.request.Request(
        _endpoint(os.environ["LLM_BASE_URL"]),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ["LLM_API_KEY"],
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        result = _extract_json(content)
    except (urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError) as exc:
        return None, exc
    return result, None


def judge_claim(claim, source_spans, stances=None):
    first_valid = None
    first_any = None
    last_error = None
    for attempt in range(MAX_JUDGE_ATTEMPTS):
        result, error = _request_judge(claim, source_spans, stances)
        if error is not None:
            last_error = error
            if attempt < MAX_JUDGE_ATTEMPTS - 1:
                LOGGER.warning(
                    "judge_claim attempt %d failed: %s",
                    attempt + 1, error,
                )
            continue
        if first_any is None:
            first_any = result
        raw_verdict = str(result.get("verdict", "")).strip()
        if not raw_verdict or raw_verdict not in VERDICTS:
            last_error = ValueError("missing or invalid verdict: %r" % raw_verdict)
            if attempt < MAX_JUDGE_ATTEMPTS - 1:
                LOGGER.warning(
                    "judge_claim attempt %d returned no usable verdict: %r",
                    attempt + 1, raw_verdict,
                )
            continue
        if first_valid is None:
            first_valid = result
        elif str(first_valid.get("verdict", "")).strip() != raw_verdict:
            LOGGER.warning(
                "judge_claim inconsistent verdicts: first=%r later=%r; using first",
                str(first_valid.get("verdict", "")).strip(), raw_verdict,
            )
        break

    if first_valid is None and first_any is None:
        return {
            "verdict": "ERROR",
            "support_type": "none",
            "matched_role": "",
            "evidence_quote": "",
            "explanation": "%s: %s" % (
                type(last_error if last_error is not None else ValueError()).__name__,
                last_error if last_error is not None else "judge returned no result",
            ),
            "tradition_hint": "",
        }

    result = first_valid if first_valid is not None else first_any

    verdict = str(result.get("verdict", "")).strip()
    support_type = str(result.get("support_type", "")).strip().lower()
    role = str(result.get("matched_role", "")).strip()
    quote = str(result.get("evidence_quote", "")).strip()
    explanation = str(result.get("explanation", "")).strip()
    raw_hint = result.get("tradition_hint", "")
    tradition_hint = raw_hint.strip() if isinstance(raw_hint, str) else ""

    if verdict not in VERDICTS:
        verdict = "未被覆盖"
        explanation = ("[非法 verdict 已归为未被覆盖] " + explanation).strip()
    if support_type not in SUPPORT_TYPES:
        support_type = "none"
        explanation = ("[非法 support_type 已归为 none] " + explanation).strip()
    if verdict == "属于另一诠释" and (
        not tradition_hint or (stances and tradition_hint not in stances)
    ):
        verdict = "未被覆盖"
        tradition_hint = ""
        explanation = ("[属于另一诠释缺少有效 tradition_hint，已降级为未被覆盖] " + explanation).strip()
    if verdict in ("矛盾", "未被覆盖", "属于另一诠释"):
        support_type = "none"
    elif verdict == "支持" and support_type == "none":
        support_type = "inference"
        explanation = ("[支持但 support_type=none，归为 inference] " + explanation).strip()
    if verdict in ("未被覆盖", "属于另一诠释"):
        role = ""
    elif role not in ROLES:
        role = ""
    if quote and verdict not in ("未被覆盖", "属于另一诠释"):
        haystack = " ".join(_normalize(s["text"]) for s in source_spans)
        if _normalize(quote) not in haystack:
            explanation = ("[evidence_quote 未在 source_spans 中逐字命中] " + explanation).strip()
    if verdict != "属于另一诠释":
        tradition_hint = ""
    if verdict in ("未被覆盖", "属于另一诠释"):
        quote = ""

    return {
        "verdict": verdict,
        "support_type": support_type,
        "matched_role": role,
        "evidence_quote": quote,
        "explanation": explanation,
        "tradition_hint": tradition_hint,
    }


def split_sentences(text):
    parts = re.split(r"[。！？；;!?.]+", text)
    return [p.strip() for p in parts if p.strip()]


def lang_of(text):
    return "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"


def main():
    missing = [n for n in ("LLM_API_KEY", "LLM_BASE_URL") if not os.environ.get(n)]
    if missing:
        print("=" * 74)
        print("未设置环境变量：%s" % "、".join(missing))
        print("已停止，未调用 LLM，未写出 results.jsonl。")
        print("")
        print("请先在当前会话设置（PowerShell，仅本会话生效）：")
        if "LLM_API_KEY" in missing:
            print('  $env:LLM_API_KEY = "<your-key>"')
        if "LLM_BASE_URL" in missing:
            print('  $env:LLM_BASE_URL = "https://<host>/v1"')
        print('  # 可选：$env:LLM_MODEL = "<model-name>"')
        print("")
        print("然后重新运行：")
        print('  python "C:\\Users\\cashrus\\Documents\\Codex\\.kb\\app\\judge_test.py"')
        print("=" * 74)
        return 2

    with open(CONCEPT_PATH, encoding="utf-8") as f:
        concept = json.load(f)
    spans = concept["source_spans"]

    with open(CASES_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    print("endpoint : %s" % _endpoint(os.environ["LLM_BASE_URL"]))
    print("model    : %s" % os.environ.get("LLM_MODEL", "deepseek-v4-pro"))
    print("spans    : %d  %s" % (len(spans), [(s["segment_index"], s["role"]) for s in spans]))
    print("cases    : %d" % len(cases))
    print()

    rows = []
    for case in cases:
        sentences = split_sentences(case["input"])
        expected = case.get("expected") or []
        if len(sentences) != len(expected):
            print(
                "[warn] case %s: %d sentences vs %d expected"
                % (case["id"], len(sentences), len(expected))
            )
        for i, sentence in enumerate(sentences):
            result = judge_claim(sentence, spans, concept.get("stances"))
            rows.append(
                {
                    "case_id": "%s#%d" % (case["id"], i + 1),
                    "claim": sentence,
                    "verdict": result["verdict"],
                    "support_type": result["support_type"],
                    "matched_role": result["matched_role"],
                    "evidence_quote": result["evidence_quote"],
                    "explanation": result["explanation"],
                    "expected_verdict": expected[i] if i < len(expected) else "",
                }
            )
            print(
                "  %-28s %-8s %-12s %-13s expected=%s"
                % (rows[-1]["case_id"], result["verdict"], result["support_type"],
                   result["matched_role"], rows[-1]["expected_verdict"])
            )

    with open(RESULTS_PATH, "w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    def accuracy(lang):
        subset = [r for r in rows if lang_of(r["claim"]) == lang and r["expected_verdict"]]
        hit = sum(1 for r in subset if r["verdict"] == r["expected_verdict"])
        return hit, len(subset)

    print()
    print("wrote %s (%d rows)" % (RESULTS_PATH, len(rows)))
    for lang, label in (("en", "英文"), ("zh", "中文")):
        hit, total = accuracy(lang)
        print("%s: %d/%d" % (label, hit, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
