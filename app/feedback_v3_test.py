# -*- coding: utf-8 -*-
"""Offline tests for the agenda-setting v3 feedback layer."""

import io
import json
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import feedback_v3


CARD_PATH = APP_DIR.parent / "v2" / "agenda-setting.json"


def load_card():
    return json.loads(CARD_PATH.read_text(encoding="utf-8"))


def required_map(card):
    return {item["id"]: item for item in card["key_elements_required"]}


def missing_items(card, ids):
    required = required_map(card)
    return [
        {
            "id": element_id,
            "standard_statement": required[element_id]["standard_statement"],
        }
        for element_id in ids
    ]


def point(
    span,
    *,
    coverage="knowledge_backed",
    verdict="对",
    covered=None,
    missing=None,
    ai_judged=False,
):
    item = {
        "claim_span": span,
        "subject": "新闻媒体",
        "card_ref": ["checkpoints[C1]", "checkpoints[C8]", "core_definition[E1]"],
        "coverage_level": coverage,
        "verdict": verdict,
        "error_type": {"primary": "无", "secondary": None},
        "evidence_gap": None,
        "correction": "依据 core_definition[E1] 补充测量指标。",
        "covered_key_elements": list(covered or []),
        "missing_key_elements": list(missing or []),
    }
    if ai_judged:
        item.update(
            {
                "ai_generated": True,
                "unverified": True,
                "classic_definition_comparison": "符合相邻传统，但不在本地经典定义内。",
                "deviation_note": "主体或机制属于相邻扩展。",
            }
        )
    return item


class FeedbackV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.card = load_card()

    def partial_diagnosis(self):
        claim = "议程设置就是媒体报道让某些议题变重要。"
        return {
            "concept": "agenda-setting",
            "claim": claim,
            "overall": "部分对",
            "points": [
                point(
                    claim,
                    coverage="knowledge_backed",
                    verdict="部分对",
                    covered=["K1", "K2"],
                    missing=missing_items(self.card, ["K3", "K4", "K5"]),
                )
            ],
            "summary": "内部摘要，不应进入反馈 prompt。",
        }

    def pass_diagnosis(self):
        claim = "议程设置研究媒体对某些对象或属性的突出报道如何改变公众的重要性判断。"
        required_ids = list(required_map(self.card))
        return {
            "concept": "agenda-setting",
            "claim": claim,
            "overall": "对",
            "points": [
                point(
                    claim,
                    coverage="knowledge_backed",
                    verdict="对",
                    covered=required_ids,
                    missing=[],
                )
            ],
            "summary": "内部摘要，不应进入反馈 prompt。",
        }

    def ai_judged_diagnosis(self):
        claim = "算法推荐通过反复展示某些议题，影响公众对这些议题重要性的判断。"
        required_ids = list(required_map(self.card))
        return {
            "concept": "agenda-setting",
            "claim": claim,
            "overall": "对",
            "points": [
                point(
                    claim,
                    coverage="ai_judged",
                    verdict="对",
                    covered=required_ids,
                    missing=[],
                    ai_judged=True,
                )
            ],
            "summary": "内部摘要，不应进入反馈 prompt。",
        }

    def offtopic_diagnosis(self):
        claim = "人们因为害怕被孤立，所以不敢表达少数意见。"
        return {
            "concept": "agenda-setting",
            "claim": claim,
            "overall": "错",
            "points": [
                {
                    "claim_span": claim,
                    "subject": "跑题（识别为：沉默的螺旋）",
                    "card_ref": ["core_definition[E1]"],
                    "coverage_level": "undetermined",
                    "verdict": "错",
                    "error_type": {"primary": "理解错误", "secondary": None},
                    "covered_key_elements": [],
                    "missing_key_elements": [],
                    "evidence_gap": (
                        "跑题：claim 讨论的是沉默的螺旋，与当前要考察的 "
                        "agenda-setting 不符。"
                    ),
                    "correction": "你似乎混淆了概念。",
                }
            ],
            "summary": "回答的是另一个概念，需要重新确认作答概念。",
        }

    def offtopic_text(self):
        return (
            "你这句话回答的不是议程设置，而是沉默的螺旋。你是不是混淆了这两个概念？\n\n"
            "议程设置主要研究媒体对议题显著性的转移，而不是人对被孤立的恐惧如何影响意见表达。\n\n"
            "请确认你要作答的概念，然后重新作答。"
        )

    def partial_text(self):
        required = required_map(self.card)
        claim = "议程设置就是媒体报道让某些议题变重要。"
        return (
            "你这次的整体判断是部分对。\n\n"
            f"你在“{claim}”里答到了媒体端显著性分配和公众端显著性结果。\n\n"
            "你漏掉的是转移/因果链路，标准表述是："
            f"{required['K3']['standard_statement']}"
            "层次区分（第一层/第二层/网络），标准表述是："
            f"{required['K4']['standard_statement']}"
            "概念边界（不是观点灌输/不是 priming），标准表述是："
            f"{required['K5']['standard_statement']}\n\n"
            "这个概念的发展脉络是：第一层议程设置、第二层议程设置、网络议程设置。\n\n"
            "请根据以上要点重新作答。"
        )

    def pass_text(self, *, ai_mark=False):
        claim = "议程设置研究媒体对某些对象或属性的突出报道如何改变公众的重要性判断。"
        prefix = "这是 AI 提供的参考表述，未核验。" if ai_mark else ""
        return (
            f"你这次的整体判断是对。{prefix}你在“{claim}”里答到了媒体端显著性分配、"
            "公众端显著性结果、转移/因果链路、层次区分和概念边界。\n\n"
            "这个概念从第一层议程设置发展到第二层议程设置，再到网络议程设置。\n\n"
            "这一题通过。"
        )

    def test_render_prompt_removes_correction_and_summary(self):
        template = "{{DIAGNOSIS_JSON}}\n---\n{{KNOWLEDGE_CARD_JSON}}"
        rendered = feedback_v3.render_feedback_prompt(
            template, self.partial_diagnosis(), self.card
        )
        diagnosis_part = rendered.split("---", 1)[0]
        self.assertNotIn("内部摘要", diagnosis_part)
        self.assertNotIn('"correction"', diagnosis_part)
        self.assertIn("key_elements_required", rendered)

    def test_missing_element_arrays_are_rejected(self):
        diagnosis = self.pass_diagnosis()
        diagnosis["points"][0].pop("covered_key_elements")
        diagnosis["points"][0].pop("missing_key_elements")
        errors = feedback_v3.validate_diagnosis_input(
            diagnosis["claim"], diagnosis, self.card
        )
        self.assertTrue(any("covered_key_elements" in error for error in errors))
        self.assertTrue(any("missing_key_elements" in error for error in errors))

    def test_repair_fills_unclassified_required_element_and_downgrades_overall(self):
        diagnosis = self.pass_diagnosis()
        diagnosis["points"][0]["covered_key_elements"] = ["K1", "K2", "K3", "K4"]
        diagnosis["points"][0]["missing_key_elements"] = []

        repaired, repairs = feedback_v3.repair_diagnosis_coverage(
            diagnosis, self.card
        )

        self.assertEqual(repaired["overall"], "部分对")
        missing_ids = [
            item["id"] for item in repaired["points"][0]["missing_key_elements"]
        ]
        self.assertEqual(missing_ids, ["K5"])
        self.assertEqual(
            repaired["points"][0]["missing_key_elements"][0]["standard_statement"],
            required_map(self.card)["K5"]["standard_statement"],
        )
        self.assertTrue(any("K5" in repair for repair in repairs))
        self.assertEqual(
            feedback_v3.validate_diagnosis_input(
                repaired["claim"], repaired, self.card
            ),
            [],
        )

    def test_repair_removes_stale_missing_when_element_is_covered(self):
        diagnosis = self.pass_diagnosis()
        diagnosis["points"][0]["missing_key_elements"] = missing_items(
            self.card, ["K5"]
        )

        repaired, repairs = feedback_v3.repair_diagnosis_coverage(
            diagnosis, self.card
        )

        self.assertEqual(repaired["overall"], "对")
        self.assertEqual(repaired["points"][0]["missing_key_elements"], [])
        self.assertTrue(any("K5" in repair for repair in repairs))
        self.assertEqual(
            feedback_v3.validate_diagnosis_input(
                repaired["claim"], repaired, self.card
            ),
            [],
        )

    def test_repair_is_idempotent_and_leaves_offtopic_untouched(self):
        diagnosis = self.pass_diagnosis()
        diagnosis["points"][0]["covered_key_elements"] = ["K1", "K2", "K3", "K4"]
        diagnosis["points"][0]["missing_key_elements"] = []

        first, _ = feedback_v3.repair_diagnosis_coverage(diagnosis, self.card)
        second, second_repairs = feedback_v3.repair_diagnosis_coverage(
            first, self.card
        )
        self.assertEqual(first, second)
        self.assertEqual(second_repairs, [])

        offtopic = self.offtopic_diagnosis()
        untouched, offtopic_repairs = feedback_v3.repair_diagnosis_coverage(
            offtopic, self.card
        )
        self.assertEqual(untouched, offtopic)
        self.assertEqual(offtopic_repairs, [])

    def test_feedback_generation_repairs_inconsistent_coverage_before_llm(self):
        diagnosis = self.pass_diagnosis()
        diagnosis["points"][0]["covered_key_elements"] = ["K1", "K2", "K3", "K4"]
        diagnosis["points"][0]["missing_key_elements"] = []

        with patch.object(
            feedback_v3,
            "_chat_completion",
            side_effect=RuntimeError("stop-after-input-validation"),
        ):
            result = feedback_v3.generate_feedback_v3(
                diagnosis["claim"], diagnosis, self.card, log=False
            )

        self.assertTrue(result.degraded)
        self.assertIn("stop-after-input-validation", result.error)
        self.assertNotIn("必需要素未全部覆盖", result.error)

    def test_partial_feedback_accepts(self):
        diagnosis = self.partial_diagnosis()
        errors = feedback_v3.validate_feedback_text(
            self.partial_text(), diagnosis, self.card
        )
        self.assertEqual(errors, [])

    def test_partial_feedback_requires_reanswer_ending(self):
        diagnosis = self.partial_diagnosis()
        text = self.partial_text().replace(
            feedback_v3.REANSWER_END, "这次先到这里。"
        )
        errors = feedback_v3.validate_feedback_text(text, diagnosis, self.card)
        self.assertTrue(any("最后一句" in error for error in errors))

    def test_pass_feedback_accepts(self):
        diagnosis = self.pass_diagnosis()
        errors = feedback_v3.validate_feedback_text(
            self.pass_text(), diagnosis, self.card
        )
        self.assertEqual(errors, [])

    def test_pass_feedback_requires_pass_ending(self):
        diagnosis = self.pass_diagnosis()
        text = self.pass_text().replace(feedback_v3.PASS_END, "本次通过。")
        errors = feedback_v3.validate_feedback_text(text, diagnosis, self.card)
        self.assertTrue(any("这一题通过" in error for error in errors))

    def test_offtopic_feedback_accepts_without_regular_sections(self):
        diagnosis = self.offtopic_diagnosis()
        self.assertTrue(feedback_v3.is_offtopic_diagnosis(diagnosis))
        self.assertEqual(
            feedback_v3.validate_diagnosis_input(
                diagnosis["claim"], diagnosis, self.card
            ),
            [],
        )
        self.assertEqual(
            feedback_v3.validate_feedback_text(
                self.offtopic_text(), diagnosis, self.card
            ),
            [],
        )

    def test_offtopic_input_skips_regular_schema_fields(self):
        claim = "人们因为害怕被孤立，所以不敢表达少数意见。"
        diagnosis = {
            "concept": "agenda-setting",
            "claim": claim,
            "overall": "错",
            "points": [
                {
                    "subject": "跑题（识别为：沉默的螺旋）",
                    "evidence_gap": "跑题：claim 讨论的是沉默的螺旋。",
                }
            ],
        }
        self.assertEqual(
            feedback_v3.validate_diagnosis_input(claim, diagnosis, self.card), []
        )

    def test_offtopic_feedback_requires_fixed_ending(self):
        diagnosis = self.offtopic_diagnosis()
        text = self.offtopic_text().replace(
            feedback_v3.OFFTOPIC_END, "请重新作答。"
        )
        errors = feedback_v3.validate_feedback_text(text, diagnosis, self.card)
        self.assertTrue(any("跑题反馈最后一句" in error for error in errors))

    def test_offtopic_feedback_requires_confusion_mention(self):
        diagnosis = self.offtopic_diagnosis()
        text = (
            "你这句话回答的不是议程设置。\n\n"
            "请确认你要作答的概念，然后重新作答。"
        )
        errors = feedback_v3.validate_feedback_text(text, diagnosis, self.card)
        self.assertTrue(any("概念混淆" in error for error in errors))

    def test_mocked_offtopic_output_is_not_degraded(self):
        diagnosis = self.offtopic_diagnosis()
        response = {
            "content": self.offtopic_text(),
            "returned_model": "mock",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        with patch.object(feedback_v3, "_chat_completion", return_value=response):
            result = feedback_v3.generate_feedback_v3(
                diagnosis["claim"], diagnosis, self.card, log=False
            )
        self.assertFalse(result.degraded)
        self.assertEqual(result.validation_errors, [])
        self.assertEqual(result.text, self.offtopic_text())

    def test_offtopic_model_failure_uses_offtopic_fallback(self):
        diagnosis = self.offtopic_diagnosis()
        with patch.object(
            feedback_v3,
            "_chat_completion",
            side_effect=RuntimeError("mock network failure"),
        ):
            result = feedback_v3.generate_feedback_v3(
                diagnosis["claim"], diagnosis, self.card, log=False
            )
        self.assertTrue(result.degraded)
        self.assertIn("混淆", result.text)
        self.assertTrue(result.text.rstrip().endswith(feedback_v3.OFFTOPIC_END))

    def test_forbidden_internal_field_is_rejected(self):
        diagnosis = self.partial_diagnosis()
        text = self.partial_text() + "\ncard_ref: checkpoints[C1]"
        errors = feedback_v3.validate_feedback_text(text, diagnosis, self.card)
        self.assertTrue(any("card_ref" in error for error in errors))
        self.assertTrue(any("字段路径" in error for error in errors))

    def test_ai_judged_requires_marker(self):
        diagnosis = self.ai_judged_diagnosis()
        original_claim = "议程设置研究媒体对某些对象或属性的突出报道如何改变公众的重要性判断。"
        ai_claim = "算法推荐通过反复展示某些议题，影响公众对这些议题重要性的判断。"
        without_marker = self.pass_text(ai_mark=False).replace(
            original_claim, ai_claim
        )
        errors = feedback_v3.validate_feedback_text(
            without_marker, diagnosis, self.card
        )
        self.assertTrue(any("AI 生成/未核验" in error for error in errors))

        with_marker = self.pass_text(ai_mark=True).replace(
            original_claim, ai_claim
        )
        errors = feedback_v3.validate_feedback_text(
            with_marker, diagnosis, self.card
        )
        self.assertEqual(errors, [])

    def test_missing_arrays_fall_back_without_crashing(self):
        diagnosis = self.pass_diagnosis()
        diagnosis["points"][0].pop("covered_key_elements")
        diagnosis["points"][0].pop("missing_key_elements")
        result = feedback_v3.generate_feedback_v3(
            diagnosis["claim"], diagnosis, self.card, log=False
        )
        self.assertTrue(result.degraded)
        self.assertTrue(result.text.rstrip().endswith(feedback_v3.REANSWER_END))
        self.assertIn("没有提供要素覆盖信息", result.text)
        self.assertIn("covered_key_elements", result.error or "")

    def test_mocked_llm_success_keeps_validation_and_usage(self):
        diagnosis = self.partial_diagnosis()
        response = {
            "content": self.partial_text(),
            "returned_model": "deepseek-flash",
            "finish_reason": "stop",
            "usage": {
                "prompt_tokens": 123,
                "completion_tokens": 45,
                "total_tokens": 168,
            },
        }
        stderr = io.StringIO()
        with patch.object(
            feedback_v3, "_chat_completion", return_value=response
        ), redirect_stderr(stderr):
            result = feedback_v3.generate_feedback_v3(
                diagnosis["claim"], diagnosis, self.card, log=True
            )
        self.assertFalse(result.degraded)
        self.assertEqual(result.validation_errors, [])
        self.assertEqual(result.usage["prompt_tokens"], 123)
        self.assertEqual(result.returned_model, "deepseek-flash")
        log = json.loads(stderr.getvalue().strip())
        self.assertEqual(log["event"], "feedback_v3")
        self.assertEqual(log["prompt_tokens"], 123)
        self.assertFalse(log["degraded"])

    def test_mocked_llm_failure_uses_element_fallback(self):
        diagnosis = self.partial_diagnosis()
        with patch.object(
            feedback_v3,
            "_chat_completion",
            side_effect=RuntimeError("mock network failure"),
        ):
            result = feedback_v3.generate_feedback_v3(
                diagnosis["claim"], diagnosis, self.card, log=False
            )
        self.assertTrue(result.degraded)
        self.assertIn("你漏掉的是", result.text)
        self.assertIn(
            required_map(self.card)["K3"]["standard_statement"], result.text
        )
        self.assertTrue(result.text.rstrip().endswith(feedback_v3.REANSWER_END))

    def test_invalid_llm_output_degrades_and_records_validation_errors(self):
        diagnosis = self.partial_diagnosis()
        response = {
            "content": self.partial_text() + "\ncard_ref: checkpoints[C1]",
            "returned_model": "deepseek-flash",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }
        with patch.object(feedback_v3, "_chat_completion", return_value=response):
            result = feedback_v3.generate_feedback_v3(
                diagnosis["claim"], diagnosis, self.card, log=False
            )
        self.assertTrue(result.degraded)
        self.assertTrue(result.validation_errors)
        self.assertTrue(any("card_ref" in error for error in result.validation_errors))
        self.assertTrue(result.text.rstrip().endswith(feedback_v3.REANSWER_END))

    def test_missing_claim_span_retries_once_with_literal_quote_instruction(self):
        diagnosis = self.partial_diagnosis()
        claim = diagnosis["claim"]
        paraphrased = self.partial_text().replace(
            claim, "你提到媒体报道会让某些议题变得重要"
        )
        responses = [
            {
                "content": paraphrased,
                "returned_model": "mock",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            },
            {
                "content": self.partial_text(),
                "returned_model": "mock",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 60,
                    "total_tokens": 180,
                },
            },
        ]
        with patch.object(
            feedback_v3, "_chat_completion", side_effect=responses
        ) as chat:
            result = feedback_v3.generate_feedback_v3(
                claim, diagnosis, self.card, log=False
            )

        self.assertFalse(result.degraded)
        self.assertEqual(result.text, self.partial_text())
        self.assertEqual(result.attempts, 2)
        self.assertEqual(chat.call_count, 2)
        self.assertEqual(result.usage["prompt_tokens"], 220)
        self.assertEqual(result.usage["completion_tokens"], 110)
        retry_prompt = chat.call_args_list[1].args[0]
        self.assertIn(claim, retry_prompt)
        self.assertIn("不得改成第二人称", retry_prompt)

    def test_missing_claim_spans_after_retry_are_deterministically_quoted(self):
        spans = [f"第{index}个主张成立" for index in range(1, 8)]
        claim = "，".join(spans) + "。"
        required_ids = list(required_map(self.card))
        diagnosis = {
            "concept": "agenda-setting",
            "claim": claim,
            "overall": "部分对",
            "points": [
                point(
                    span,
                    verdict="部分对",
                    covered=required_ids,
                    missing=[],
                )
                for span in spans
            ],
        }
        included = [0, 2, 3, 4, 5]
        model_text = (
            "你这次的整体判断是部分对。你答到了媒体端显著性分配和公众端显著性结果。\n\n"
            + "；".join(f"你在“{spans[index]}”里说到了对应内容" for index in included)
            + "。\n\n"
            "这个概念的发展脉络是：第一层议程设置、第二层议程设置和网络议程设置。\n\n"
            "请根据以上要点重新作答。"
        )
        response = {
            "content": model_text,
            "returned_model": "mock",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }
        with patch.object(
            feedback_v3, "_chat_completion", return_value=response
        ) as chat:
            result = feedback_v3.generate_feedback_v3(
                claim, diagnosis, self.card, log=False
            )

        self.assertFalse(result.degraded)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(chat.call_count, 2)
        self.assertEqual(result.validation_errors, [])
        self.assertEqual(result.raw_text, model_text)
        self.assertIn("另外，还有几处你的原话需要逐字核对", result.text)
        for span in spans:
            self.assertIn(span, result.text)
        self.assertTrue(result.text.rstrip().endswith(feedback_v3.REANSWER_END))

    def test_non_claim_span_validation_error_does_not_retry(self):
        diagnosis = self.partial_diagnosis()
        response = {
            "content": self.partial_text() + "\ncard_ref: checkpoints[C1]",
            "returned_model": "mock",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }
        with patch.object(
            feedback_v3, "_chat_completion", return_value=response
        ) as chat:
            result = feedback_v3.generate_feedback_v3(
                diagnosis["claim"], diagnosis, self.card, log=False
            )

        self.assertTrue(result.degraded)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(chat.call_count, 1)

    def test_missing_ai_mark_is_repaired_together_with_claim_spans(self):
        spans = [f"第{index}个判断" for index in range(1, 8)]
        claim = "，".join(spans) + "。"
        required_ids = list(required_map(self.card))
        diagnosis = {
            "concept": "agenda-setting",
            "claim": claim,
            "overall": "部分对",
            "points": [
                point(
                    span,
                    coverage="ai_judged" if index in (1, 6) else "knowledge_backed",
                    verdict="部分对",
                    covered=required_ids,
                    missing=[],
                    ai_judged=index in (1, 6),
                )
                for index, span in enumerate(spans)
            ],
        }
        included = [0, 2, 3, 4, 5]
        model_text = (
            "你这次的整体判断是部分对。你答到了媒体端显著性分配和公众端显著性结果。\n\n"
            + "；".join(f"你在“{spans[index]}”里说到了对应内容" for index in included)
            + "。\n\n"
            "这个概念的发展脉络是：第一层议程设置、第二层议程设置和网络议程设置。\n\n"
            "请根据以上要点重新作答。"
        )
        response = {
            "content": model_text,
            "returned_model": "mock",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }
        with patch.object(
            feedback_v3, "_chat_completion", return_value=response
        ) as chat:
            result = feedback_v3.generate_feedback_v3(
                claim, diagnosis, self.card, log=False
            )

        self.assertFalse(result.degraded)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(chat.call_count, 2)
        self.assertEqual(result.validation_errors, [])
        self.assertTrue(feedback_v3._has_ai_reference_mark(result.text))
        for span in spans:
            self.assertIn(span, result.text)

    def test_corrected_v03_schema_compliant_diagnosis_reaches_pass_branch(self):
        claim = (
            "议程设置研究媒体对某些对象或属性的突出报道，如何让公众对这些对象或属性的"
            "重要性判断发生变化，包括第一层对象显著性、第二层属性显著性和网络议程设置，"
            "它不直接决定公众支持谁，也不等同于 priming。"
        )
        spans = [
            "议程设置研究媒体对某些对象或属性的突出报道，如何让公众对这些对象或属性的重要性判断发生变化",
            "包括第一层对象显著性、第二层属性显著性和网络议程设置",
            "它不直接决定公众支持谁",
            "也不等同于 priming",
        ]
        coverage = [["K1", "K2", "K3"], ["K4"], ["K5"], ["K5"]]
        diagnosis = {
            "concept": "agenda-setting",
            "claim": claim,
            "overall": "对",
            "points": [
                point(span, covered=ids, missing=[])
                for span, ids in zip(spans, coverage)
            ],
        }
        text = (
            "你这次的整体判断是对，答到了全部必需要素。你在"
            f"“{spans[0]}”里说清了媒体端对对象和属性的显著性分配，以及公众端重要性判断的变化；"
            f"在“{spans[1]}”里覆盖了三个层次；"
            f"在“{spans[2]}”里划清了效果边界；"
            f"在“{spans[3]}”里把它与 priming 区分开。"
            "这些说法合起来，把议程设置的核心链路和概念边界都答到了。\n\n"
            "这个概念的发展脉络是：第一层议程设置关注对象显著性，第二层议程设置转向属性显著性，"
            "网络议程设置进一步关注对象与属性之间关联网络的转移；你这次三层都点到了。\n\n"
            "这一题通过。"
        )
        response = {
            "content": text,
            "returned_model": "mock",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        self.assertEqual(
            feedback_v3.validate_diagnosis_input(claim, diagnosis, self.card), []
        )
        self.assertEqual(
            feedback_v3.validate_feedback_text(text, diagnosis, self.card), []
        )
        with patch.object(feedback_v3, "_chat_completion", return_value=response):
            result = feedback_v3.generate_feedback_v3(
                claim, diagnosis, self.card, log=False
            )
        self.assertFalse(result.degraded)
        self.assertEqual(result.validation_errors, [])
        self.assertTrue(result.text.rstrip().endswith(feedback_v3.PASS_END))


if __name__ == "__main__":
    unittest.main(verbosity=2)
