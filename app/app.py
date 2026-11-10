# -*- coding: utf-8 -*-
"""Minimal Streamlit demo for the philosophy concept learning app."""

from __future__ import annotations

import glob
import html
import json
import os
import re
import sys
from difflib import SequenceMatcher

import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.dirname(APP_DIR)
CONCEPTS_DIR = os.path.join(KB_DIR, "concepts")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from judge_test import judge_claim, split_sentences  # noqa: E402
from feedback import generate_feedback  # noqa: E402

st.set_page_config(
    page_title="西方哲学概念学习 Demo",
    page_icon="📜",
    layout="wide",
)

VERDICT_STYLE = {
    "支持": ("#15803d", "#ffffff"),
    "矛盾": ("#b91c1c", "#ffffff"),
    "属于另一诠释": ("#c2410c", "#ffffff"),
    "未被覆盖": ("#6b7280", "#ffffff"),
}


def load_concepts():
    concepts = []
    for path in sorted(glob.glob(os.path.join(CONCEPTS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["_slug"] = os.path.splitext(os.path.basename(path))[0]
        concepts.append(data)
    return concepts


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").replace("*", "")).strip().lower()


def align_standard_def(quote, spans):
    """Return the closest real substring/sentence from source_spans."""
    quote = (quote or "").strip()
    if not quote:
        return ""

    for span in spans:
        text = span.get("text") or ""
        if quote in text:
            return quote
        tokens = quote.split()
        if tokens:
            pattern = r"\s+".join(re.escape(token) for token in tokens)
            match = re.search(pattern, text)
            if match:
                return match.group(0)

    normalized_quote = normalize_text(quote)
    best_ratio = 0.0
    best_sentence = ""
    for span in spans:
        text = span.get("text") or ""
        for sentence in re.split(r"(?<=[.!?])\s+|\n{2,}", text):
            normalized_sentence = normalize_text(sentence)
            if len(normalized_sentence) < 20:
                continue
            ratio = SequenceMatcher(None, normalized_quote, normalized_sentence).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_sentence = sentence.strip()
    if best_ratio >= 0.45:
        return best_sentence
    return quote


def verdict_badge(verdict):
    background, foreground = VERDICT_STYLE.get(verdict, ("#374151", "#ffffff"))
    return (
        '<span style="display:inline-block;padding:0.2rem 0.65rem;'
        'border-radius:999px;background:%s;color:%s;font-weight:600;">%s</span>'
        % (background, foreground, html.escape(str(verdict)))
    )


def clear_state():
    st.session_state["claim_input"] = ""
    st.session_state["results"] = None
    st.session_state["result_slug"] = None


concepts = load_concepts()
if not concepts:
    st.error("没有在 concepts/ 下找到概念 JSON。")
    st.stop()

if "results" not in st.session_state:
    st.session_state["results"] = None
if "result_slug" not in st.session_state:
    st.session_state["result_slug"] = None
if "claim_input" not in st.session_state:
    st.session_state["claim_input"] = ""

terms = [c["term"] for c in concepts]
term_to_concept = {c["term"]: c for c in concepts}
selected_term = st.sidebar.selectbox("选择概念", terms)
concept = term_to_concept[selected_term]

if st.session_state.get("result_slug") not in (None, concept["_slug"]):
    st.session_state["results"] = None
    st.session_state["result_slug"] = None

st.sidebar.markdown("**%s**" % concept.get("term_en", ""))
st.sidebar.caption(concept.get("short_def", ""))
st.sidebar.caption("已加载 %d 个概念" % len(concepts))

if not os.environ.get("LLM_API_KEY") or not os.environ.get("LLM_BASE_URL"):
    st.sidebar.warning("LLM_API_KEY / LLM_BASE_URL 未设置，提交将无法调用模型。")

st.title("西方哲学概念学习 Demo")
st.caption("输入你的理解，系统会依据课程知识库给出判定与结构化反馈。")

with st.container(border=True):
    st.subheader(concept.get("term", ""))
    st.markdown("**%s**" % concept.get("term_en", ""))
    st.write(concept.get("short_def", ""))

with st.form("claim_form"):
    st.text_area(
        "你的解释",
        key="claim_input",
        height=120,
        placeholder="例如：自由就是没有人阻止我做想做的事。",
    )
    submitted = st.form_submit_button("提交", type="primary")

if submitted:
    claim_text = (st.session_state.get("claim_input") or "").strip()
    if not claim_text:
        st.warning("请先输入你的解释。")
    elif not os.environ.get("LLM_API_KEY") or not os.environ.get("LLM_BASE_URL"):
        st.error("缺少 LLM_API_KEY / LLM_BASE_URL，无法调用判定与反馈模型。")
    else:
        claims = split_sentences(claim_text)
        results = []
        with st.spinner("正在判定并生成反馈……"):
            for claim in claims:
                judged = judge_claim(
                    claim,
                    concept.get("source_spans") or [],
                    concept.get("stances") or [],
                )
                feedback = generate_feedback(
                    claim,
                    judged["verdict"],
                    judged["support_type"],
                    judged["matched_role"],
                    judged["evidence_quote"],
                    judged["tradition_hint"],
                    concept,
                )
                aligned = align_standard_def(
                    feedback.get("standard_def", ""),
                    concept.get("source_spans") or [],
                )
                results.append(
                    {
                        "claim": claim,
                        "judged": judged,
                        "feedback": feedback,
                        "aligned_standard_def": aligned,
                    }
                )
        st.session_state["results"] = results
        st.session_state["result_slug"] = concept["_slug"]

results = st.session_state.get("results")
if results and st.session_state.get("result_slug") == concept["_slug"]:
    st.subheader("判定与反馈")
    for index, item in enumerate(results, 1):
        judged = item["judged"]
        feedback = item["feedback"]
        verdict = judged.get("verdict", "")
        with st.container(border=True):
            st.markdown("**原句 %d**" % index)
            st.write(item["claim"])
            st.markdown(
                "**verdict：** %s" % verdict_badge(verdict),
                unsafe_allow_html=True,
            )
            st.caption(
                "support_type: %s　|　matched_role: %s"
                % (
                    judged.get("support_type") or "（无）",
                    judged.get("matched_role") or "（无）",
                )
            )
            st.markdown("**复述 restatement**")
            st.write(feedback.get("restatement", ""))
            st.markdown("**标准定义 standard_def（原文对齐）**")
            st.code(item["aligned_standard_def"], language=None)
            st.markdown("**偏离说明 deviation**")
            st.write(feedback.get("deviation", ""))
            st.markdown("**严重度 severity**")
            st.write(feedback.get("severity", ""))
            st.markdown("**传统方向 direction**")
            st.write(feedback.get("direction") or "（无）")

with st.expander("查看该概念的完整知识库", expanded=False):
    st.markdown("#### source_spans")
    for footprint in concept.get("source_spans") or []:
        st.markdown(
            "**segment_index=%s　role=%s**"
            % (footprint.get("segment_index", ""), footprint.get("role", ""))
        )
        st.text(footprint.get("text", ""))

    st.markdown("#### literature")
    literature = concept.get("literature") or []
    if literature:
        for entry in literature:
            st.markdown("- %s" % entry)
    else:
        st.write("（无）")

    st.markdown("#### chain")
    st.write(concept.get("chain", ""))

    st.markdown("#### stances")
    stances = concept.get("stances") or []
    if stances:
        for stance in stances:
            st.markdown("- %s" % stance)
    else:
        st.write("（无）")

st.divider()
st.button("清空", on_click=clear_state)