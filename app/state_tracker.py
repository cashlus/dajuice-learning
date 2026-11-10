#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal in-memory retry state for the agenda-setting learning loop."""

from __future__ import annotations

from typing import Any


PASS = "PASS"
NEED_RETRY = "NEED_RETRY"
NEED_RECONFIRM = "NEED_RECONFIRM"


class LearningSession:
    """Track missing key elements across repeated answers in one learning session."""


    def __init__(self, concept: str = "agenda-setting") -> None:
        self.concept = concept
        self.missing_list: list[str] = []
        self.status = NEED_RETRY


    @staticmethod
    def _is_offtopic(diagnosis: dict[str, Any]) -> bool:
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


    @staticmethod
    def _covered_ids(diagnosis: dict[str, Any]) -> list[str]:
        result: list[str] = []
        for point in diagnosis.get("points") or []:
            if not isinstance(point, dict):
                continue
            for element_id in point.get("covered_key_elements") or []:
                if isinstance(element_id, str) and element_id not in result:
                    result.append(element_id)
        return result


    @staticmethod
    def _missing_ids(diagnosis: dict[str, Any]) -> list[str]:
        result: list[str] = []
        for point in diagnosis.get("points") or []:
            if not isinstance(point, dict):
                continue
            for item in point.get("missing_key_elements") or []:
                if not isinstance(item, dict):
                    continue
                element_id = item.get("id")
                if isinstance(element_id, str) and element_id not in result:
                    result.append(element_id)
        return result


    @staticmethod
    def _has_expression_issue(diagnosis: dict[str, Any]) -> bool:
        for point in diagnosis.get("points") or []:
            if not isinstance(point, dict):
                continue
            error_type = point.get("error_type")
            if isinstance(error_type, dict):
                for key in ("primary", "secondary"):
                    value = error_type.get(key)
                    if isinstance(value, str) and "表达问题" in value:
                        return True
            elif isinstance(error_type, str) and "表达问题" in error_type:
                return True
        return False


    def submit(self, diagnosis_json: dict[str, Any]) -> dict[str, Any]:
        """Consume one frozen diagnosis and return the next session state."""
        if not isinstance(diagnosis_json, dict):
            raise TypeError("diagnosis_json 必须是 dict")

        if self._is_offtopic(diagnosis_json):
            self.missing_list = []
            self.status = NEED_RECONFIRM
            return self._result("你这次回答的内容不属于当前概念，请确认你要作答的概念，然后重新作答。")

        overall = diagnosis_json.get("overall")
        covered = self._covered_ids(diagnosis_json)
        incoming_missing = self._missing_ids(diagnosis_json)
        expression_issue = self._has_expression_issue(diagnosis_json)
        previous_missing = list(self.missing_list)

        if overall == "对" and not expression_issue and not incoming_missing:
            self.missing_list = []
            self.status = PASS
        else:
            self.missing_list = list(incoming_missing)
            self.status = NEED_RETRY

        if self.status == PASS:
            message = "这一题通过。"
        elif expression_issue and not self.missing_list:
            message = "你理解了核心意思，但表达还不够学术。请参考标准学术表述，用更严谨的专业术语重新作答。"
        elif previous_missing and incoming_missing:
            recovered = [
                element_id
                for element_id in previous_missing
                if element_id in covered
            ]
            new_missing = [
                element_id
                for element_id in incoming_missing
                if element_id not in previous_missing
            ]
            if recovered and new_missing:
                message = (
                    "你补上了上一轮漏掉的 "
                    + "、".join(recovered)
                    + "，但这次又漏掉了前面的 "
                    + "、".join(new_missing)
                    + "。请把前后两部分一起说完整后重新作答。"
                )
            else:
                message = "请根据以上要点重新作答。"
        else:
            message = "请根据以上要点重新作答。"
        return self._result(message, covered=covered)


    def _result(self, message: str, *, covered: list[str] | None = None) -> dict[str, Any]:
        return {
            "status": self.status,
            "missing_list": list(self.missing_list),
            "message": message,
            "covered_key_elements": list(covered or []),
        }
