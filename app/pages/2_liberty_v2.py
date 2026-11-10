# -*- coding: utf-8 -*-
"""Streamlit page for the liberty v2 framework-attribution demo."""

from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
KB_DIR = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import judge_mvp  # noqa: E402


V2_PATH = KB_DIR / "v2" / "liberty_v2.json"
V1_PATH = KB_DIR / "concepts" / "liberty.json"

RESULT_STYLE = {
    "single_framework": {
        "label": "单一框架",
        "icon": "✅",
        "color": "#15803d",
        "background": "#f0fdf4",
    },
    "ambiguous_between_frameworks": {
        "label": "框架间歧义",
        "icon": "⚠️",
        "color": "#c2410c",
        "background": "#fff7ed",
    },
    "no_coverage": {
        "label": "本地知识库未覆盖",
        "icon": "⚪",
        "color": "#6b7280",
        "background": "#f9fafb",
    },
}


st.set_page_config(
    page_title="Liberty v2 判定 Demo",
    page_icon="🧭",
    layout="wide",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def result_badge(result_type: str) -> str:
    style = RESULT_STYLE.get(
        result_type,
        {
            "label": result_type or "未知结果",
            "icon": "❔",
            "color": "#374151",
            "background": "#f3f4f6",
        },
    )
    return (
        '<span style="display:inline-flex;align-items:center;gap:0.35rem;'
        'padding:0.25rem 0.7rem;border-radius:999px;'
        'background:{background};color:{color};border:1px solid {color};'
        'font-weight:700;">{icon} {label}</span>'
    ).format(
        background=style["background"],
        color=style["color"],
        icon=style["icon"],
        label=html.escape(style["label"]),
    )


def render_evidence_refs(refs: Any) -> None:
    if isinstance(refs, list) and refs:
        st.caption("证据路径：" + " · ".join("`%s`" % ref for ref in refs))


def render_result(result: dict[str, Any], guard_correction: bool) -> None:
    result_type = result.get("result_type", "")
    style = RESULT_STYLE.get(result_type)
    if style is None:
        st.error("判定失败：返回了未知的 result_type：%s" % (result_type or "（空）"))
        return

    st.subheader("判定结果")
    st.markdown(result_badge(result_type), unsafe_allow_html=True)

    with st.container(border=True):
        if result_type == "single_framework":
            st.markdown("**归属框架**")
            st.markdown("### %s" % result.get("framework", "（未提供）"))
            confusion = result.get("confusion_hit")
            st.markdown(
                "**命中常见混淆：** %s" % (confusion if confusion else "（无）")
            )
            next_question = result.get("next_question") or "（未提供）"
            st.markdown("**区分性追问：** %s" % next_question)

        elif result_type == "ambiguous_between_frameworks":
            st.markdown("**两个候选框架**")
            candidates = result.get("candidates") or []
            if candidates:
                for candidate in candidates:
                    st.markdown("- **%s**" % candidate)
            else:
                st.write("（未提供候选框架）")
            confusion = result.get("confusion_hit")
            st.markdown(
                "**命中常见混淆：** %s" % (confusion if confusion else "（无）")
            )
            next_question = result.get("next_question") or "（未提供）"
            st.markdown("**区分性追问：** %s" % next_question)

        else:
            st.markdown("**本地知识库未覆盖**")
            st.write(result.get("reason") or "（未提供原因）")

        render_evidence_refs(result.get("evidence_refs"))
        if guard_correction:
            st.caption("guard_correction：LLM 初判已由确定性守卫纠正。")


def clear_v2_state() -> None:
    st.session_state["v2_claim_input"] = ""
    st.session_state["v2_judged_claim"] = ""
    st.session_state["v2_result"] = None
    st.session_state["v2_guard_correction"] = False
    st.session_state["v2_error"] = ""


v2_concept = load_json(V2_PATH)
v1_concept = load_json(V1_PATH)

for state_key, env_key, default in (
    ("v2_llm_base_url", "LLM_BASE_URL", ""),
    ("v2_llm_api_key", "LLM_API_KEY", ""),
    ("v2_llm_model", "LLM_MODEL", "deepseek-chat"),
):
    if state_key not in st.session_state:
        st.session_state[state_key] = os.environ.get(env_key, default)

for state_key, default in (
    ("v2_claim_input", ""),
    ("v2_judged_claim", ""),
    ("v2_result", None),
    ("v2_guard_correction", False),
    ("v2_error", ""),
):
    if state_key not in st.session_state:
        st.session_state[state_key] = default

with st.sidebar:
    st.header("Liberty v2 demo")
    st.selectbox("选择概念", ["liberty"], index=0)
    st.caption("v2 demo：仅开放 liberty")
    st.markdown("**%s**" % v1_concept.get("term_en", "Liberty"))
    st.caption(v1_concept.get("short_def", ""))

    st.divider()
    st.subheader("API 配置")
    st.text_input(
        "LLM_BASE_URL",
        key="v2_llm_base_url",
        placeholder="https://api.deepseek.com/v1",
    )
    st.text_input(
        "LLM_API_KEY",
        key="v2_llm_api_key",
        type="password",
    )
    st.text_input(
        "LLM_MODEL",
        key="v2_llm_model",
        placeholder="deepseek-chat",
    )
    st.caption("配置保存在 st.session_state；提交时注入环境变量，不在文件中写入 key。")

    if not st.session_state["v2_llm_base_url"].strip() or not st.session_state[
        "v2_llm_api_key"
    ].strip():
        st.warning("LLM_BASE_URL 或 LLM_API_KEY 未填写，提交将无法调用模型。")

st.title("Liberty v2 判定 Demo")
st.caption("框架归属识别 + 常见混淆命中。v1 仍保留在主导航页。")

with st.container(border=True):
    st.subheader("liberty · v2 demo")
    st.markdown("**%s**" % v1_concept.get("term_en", "Liberty"))
    st.write(v1_concept.get("short_def", ""))
    st.markdown("**v2 核心问题**")
    st.write(v2_concept.get("core_question", ""))

with st.form("liberty_v2_claim_form"):
    st.text_area(
        "你的说法",
        key="v2_claim_input",
        height=120,
        placeholder="例如：自由是做自己想做的事。",
    )
    submitted = st.form_submit_button("判定", type="primary")

if submitted:
    claim_text = (st.session_state.get("v2_claim_input") or "").strip()
    base_url = (st.session_state.get("v2_llm_base_url") or "").strip()
    api_key = (st.session_state.get("v2_llm_api_key") or "").strip()
    model = (st.session_state.get("v2_llm_model") or "").strip()

    st.session_state["v2_error"] = ""
    if not claim_text:
        st.session_state["v2_error"] = "判定失败：请先输入你的说法。"
    elif not base_url or not api_key:
        st.session_state["v2_error"] = (
            "判定失败：缺少 LLM_BASE_URL 或 LLM_API_KEY，请在侧栏填写后再试。"
        )
    elif not model:
        st.session_state["v2_error"] = "判定失败：缺少 LLM_MODEL。"
    else:
        os.environ["LLM_BASE_URL"] = base_url
        os.environ["LLM_API_KEY"] = api_key
        os.environ["LLM_MODEL"] = model
        try:
            with st.spinner("判定中..."):
                result, guard_correction = judge_mvp.judge(
                    claim_text,
                    v2_concept,
                    model,
                    retries=1,
                )
        except Exception as exc:
            st.session_state["v2_result"] = None
            st.session_state["v2_judged_claim"] = ""
            st.session_state["v2_guard_correction"] = False
            st.session_state["v2_error"] = "判定失败：%s" % exc
        else:
            st.session_state["v2_judged_claim"] = claim_text
            st.session_state["v2_result"] = result
            st.session_state["v2_guard_correction"] = bool(guard_correction)

if st.session_state.get("v2_error"):
    st.error(st.session_state["v2_error"])

if st.session_state.get("v2_result"):
    st.markdown("**输入说法：** %s" % st.session_state.get("v2_judged_claim", ""))
    render_result(
        st.session_state["v2_result"],
        bool(st.session_state.get("v2_guard_correction")),
    )

with st.expander("查看 liberty 的知识库详情", expanded=False):
    st.markdown("#### v2 core_question")
    st.write(v2_concept.get("core_question", ""))

    st.markdown("#### v2 frameworks 与 key_spans")
    for framework in v2_concept.get("frameworks", []):
        st.markdown("**%s**" % framework.get("name", ""))
        st.write(framework.get("answers", ""))
        for span in framework.get("key_spans", []):
            st.caption(
                "source=%s　locator=%s"
                % (span.get("source", ""), span.get("locator", ""))
            )
            st.text(span.get("text", ""))

    st.markdown("#### source_spans（v1 原文）")
    for footprint in v1_concept.get("source_spans", []):
        st.markdown(
            "**segment_index=%s　role=%s**"
            % (footprint.get("segment_index", ""), footprint.get("role", ""))
        )
        st.text(footprint.get("text", ""))

    st.markdown("#### literature")
    literature = v1_concept.get("literature", [])
    if literature:
        for entry in literature:
            st.markdown("- %s" % entry)
    else:
        st.write("（无）")

    st.markdown("#### chain")
    st.write(v1_concept.get("chain", ""))

    st.markdown("#### stances")
    stances = v1_concept.get("stances", [])
    if stances:
        for stance in stances:
            st.markdown("- %s" % stance)
    else:
        st.write("（无）")

st.divider()
st.button("清空", on_click=clear_v2_state)
