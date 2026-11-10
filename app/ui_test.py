# -*- coding: utf-8 -*-
import json
from streamlit.testing.v1 import AppTest

APP = r"C:\Users\cashrus\Documents\Codex\.kb\app\app.py"
LIBERTY_TERM = "消极自由 / 积极自由"
FREEWILL_TERM = "自由意志"


def run_case(term, claim):
    at = AppTest.from_file(APP, default_timeout=240)
    at.run()
    at.selectbox[0].select(term)
    at.run()
    at.text_area[0].input(claim)
    at.button[0].click()
    at.run(timeout=240)
    print("=" * 70)
    print("term:", term)
    print("claim:", claim)
    print("exceptions:", [str(e.value) for e in at.exception])
    print("expanders:", [getattr(e, "label", "?") for e in at.expander])
    if "results" in at.session_state:
        results = at.session_state["results"]
        print("session results:", len(results) if results else 0)
        if results:
            for i, item in enumerate(results, 1):
                judged = item["judged"]
                feedback = item["feedback"]
                print("result", i, json.dumps({
                    "claim": item["claim"],
                    "verdict": judged.get("verdict"),
                    "support_type": judged.get("support_type"),
                    "matched_role": judged.get("matched_role"),
                    "feedback": feedback,
                    "aligned_standard_def": item["aligned_standard_def"],
                }, ensure_ascii=False, indent=2))
    else:
        print("session results: key missing")
    markdown_texts = [m.value for m in at.markdown]
    print("markdown with verdict:", [t for t in markdown_texts if "verdict" in t])
    return at


run_case(LIBERTY_TERM, "自由就是人可以自由地做任何不违背自我道德的事，不损害他人")
run_case(FREEWILL_TERM, "自由意志就是能够做出其他选择")