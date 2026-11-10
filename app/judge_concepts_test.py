# -*- coding: utf-8 -*-
import json, os, sys, re
sys.stdout.reconfigure(encoding="utf-8")

APP = r"C:\Users\cashrus\Documents\Codex\.kb\app"
KB = r"C:\Users\cashrus\Documents\Codex\.kb"
sys.path.insert(0, APP)
from judge_test import judge_claim, split_sentences, _normalize

CASES = [
    ("justice", "j-01", "正义就是给每个人应得的。", ["支持"]),
    ("justice", "j-02", "正义就是最大多数人的最大幸福。", ["矛盾", "未被覆盖"]),
    ("justice", "j-03", "正义关心的是个体 claims 的冲突与裁决。", ["支持"]),
    ("equality", "e-01", "平等就是所有方面都完全相同。", ["矛盾"]),
    ("equality", "e-02", "平等是两个对象在某个维度上的相同关系。", ["支持"]),
    ("equality", "e-03", "平等就是平均分配资源。", ["未被覆盖"]),
    ("epistemology", "k-01", "知识就是被证成的真信念。", ["支持"]),
    ("epistemology", "k-02", "JTB 就是知识的完整定义，没有反例。", ["矛盾"]),
    ("epistemology", "k-03", "知识要求信念、真和辩护三个条件。", ["支持"]),
]

concepts = {}
for slug in ("justice", "equality", "epistemology"):
    with open(os.path.join(KB, "concepts", slug + ".json"), encoding="utf-8") as f:
        concepts[slug] = json.load(f)

def quote_status(quote, spans):
    if not quote:
        return "empty"
    for s in spans:
        if quote in s["text"]:
            return "strict"
    hay = " ".join(_normalize(s["text"]) for s in spans)
    if _normalize(quote) in hay:
        return "normalized"
    return "MISS"

rows = []
for slug, cid, claim, expected in CASES:
    concept = concepts[slug]
    spans = concept["source_spans"]
    sentences = split_sentences(claim)
    assert len(sentences) == 1, (cid, sentences)
    result = judge_claim(sentences[0], spans)
    qs = quote_status(result["evidence_quote"], spans)
    consistent = result["verdict"] in expected
    row = {
        "case_id": cid,
        "concept": slug,
        "claim": sentences[0],
        "verdict": result["verdict"],
        "support_type": result["support_type"],
        "matched_role": result["matched_role"],
        "evidence_quote": result["evidence_quote"],
        "quote_status": qs,
        "explanation": result["explanation"],
        "expected": expected,
        "consistent": consistent,
    }
    rows.append(row)
    print("-" * 100)
    print(f"{cid} | {slug} | {row['claim']}")
    print(f"  verdict={row['verdict']}  support_type={row['support_type']}  matched_role={row['matched_role']}  expected={expected}  consistent={consistent}")
    print(f"  quote_status={qs}")
    print(f"  evidence_quote={row['evidence_quote'][:220]!r}")
    print(f"  explanation={row['explanation'][:220]}")

out_path = os.path.join(APP, "results_concepts.jsonl")
with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print()
print("wrote", out_path, len(rows), "rows")
print()
print("=== per-concept ===")
for slug in ("justice", "equality", "epistemology"):
    sub = [r for r in rows if r["concept"] == slug]
    hit = sum(1 for r in sub if r["consistent"])
    print(f"{slug}: {hit}/{len(sub)}")
print()
print("=== quote status ===")
from collections import Counter
print(Counter(r["quote_status"] for r in rows))
print()
print("=== inference explanations ===")
for r in rows:
    if r["support_type"] == "inference":
        print(r["case_id"], "|", r["explanation"][:160])
