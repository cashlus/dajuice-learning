# -*- coding: utf-8 -*-
import json
import os
import sys

APP = os.path.dirname(os.path.abspath(__file__))
if APP not in sys.path:
    sys.path.insert(0, APP)

from judge_test import judge_claim

KB = r"C:\Users\cashrus\Documents\Codex\.kb"
CONCEPT = os.path.join(KB, "concepts", "liberty.json")
CLAIM = "自由就是人可以自由地做任何不违背自我道德的事，不损害他人"


def main():
    with open(CONCEPT, encoding="utf-8") as f:
        concept = json.load(f)
    rows = []
    for i in range(1, 4):
        result = judge_claim(
            CLAIM,
            concept.get("source_spans") or [],
            concept.get("stances") or [],
        )
        row = {
            "run": i,
            "verdict": result["verdict"],
            "tradition_hint": result["tradition_hint"],
        }
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))
    keys = {(r["verdict"], r["tradition_hint"]) for r in rows}
    print("consistent:", len(keys) == 1)


if __name__ == "__main__":
    main()