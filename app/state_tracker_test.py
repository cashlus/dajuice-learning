#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Terminal walkthrough for LearningSession."""

from __future__ import annotations

import json

from state_tracker import LearningSession, NEED_RETRY, PASS


def diagnosis(overall: str, covered: list[str], missing: list[str]) -> dict:
    return {
        "overall": overall,
        "points": [
            {
                "covered_key_elements": covered,
                "missing_key_elements": [{"id": element_id} for element_id in missing],
            }
        ],
    }


def show(step: int, answer: str, result: dict) -> None:
    print(
        json.dumps(
            {
                "step": step,
                "answer": answer,
                "status": result["status"],
                "missing_list": result["missing_list"],
                "covered_key_elements": result["covered_key_elements"],
                "message": result["message"],
            },
            ensure_ascii=False,
        )
    )


def main() -> int:
    session = LearningSession()

    first = session.submit(diagnosis("部分对", ["K1", "K2"], ["K3"]))
    show(1, "答到 K1/K2，漏 K3", first)
    assert first["status"] == NEED_RETRY and first["missing_list"] == ["K3"]

    second = session.submit(diagnosis("部分对", ["K3"], ["K4"]))
    show(2, "补上 K3，仍漏 K4", second)
    assert second["status"] == NEED_RETRY and second["missing_list"] == ["K4"]

    third = session.submit(diagnosis("对", ["K4"], []))
    show(3, "补上 K4", third)
    assert third["status"] == PASS and third["missing_list"] == []

    print(json.dumps({"result": "PASS", "flow": "K3 -> K4 -> PASS"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
