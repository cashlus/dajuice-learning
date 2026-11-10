#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single-page Streamlit demo for the agenda-setting learning loop."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from diagnosis_runner import DEFAULT_CARD_PATH, diagnose  # noqa: E402
from feedback_v3 import (  # noqa: E402
    generate_feedback_v3,
    load_json,
    repair_diagnosis_coverage,
)
from state_tracker import LearningSession, PASS  # noqa: E402


CONCEPT_SLUG = "agenda-setting"
LLM_ENV = "LLM_API_KEY"
TAVILY_ENV = "TAVILY_API_KEY"


st.set_page_config(
    page_title="新媒体广告前沿 - 概念学习闭环",
    page_icon="📚",
    layout="centered",
)


@contextmanager
def _temporary_env(overrides: dict[str, str]) -> Iterator[None]:
    """Expose request-scoped keys without persisting them in process env."""
    previous = {name: os.environ.get(name) for name in overrides}
    try:
        os.environ.update(overrides)
        yield
    finally:
        for name, old_value in previous.items():
            if old_value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old_value


def _redact(value: object, secrets: Iterable[str] = ()) -> str:
    text = str(value)
    for secret in (*secrets, os.environ.get(LLM_ENV, ""), os.environ.get(TAVILY_ENV, "")):
        if secret:
            text = text.replace(secret, "[已隐藏]")
    return text


def _reset_learning() -> None:
    st.session_state["learning_session"] = LearningSession(CONCEPT_SLUG)
    st.session_state["chat_history"] = []
    st.session_state.pop("ui_error", None)


def _render_sidebar() -> tuple[str, str]:
    with st.sidebar:
        st.header("运行配置")
        llm_input = st.text_input(
            "LLM_API_KEY",
            type="password",
            key="llm_api_key_input",
            help="只用于当前 Streamlit 进程内的模型调用，不写入文件。",
        ).strip()
        tavily_input = st.text_input(
            "TAVILY_API_KEY",
            type="password",
            key="tavily_api_key_input",
            help="用于短回答或不确定回答的联网补充检索，不写入文件。",
        ).strip()

        env_llm = os.environ.get(LLM_ENV, "").strip()
        env_tavily = os.environ.get(TAVILY_ENV, "").strip()
        if env_llm and not llm_input:
            st.caption("LLM_API_KEY：已从环境变量读取")
        if env_tavily and not tavily_input:
            st.caption("TAVILY_API_KEY：已从环境变量读取")

        st.button(
            "重置本次学习",
            on_click=_reset_learning,
            use_container_width=True,
        )
        st.caption("密钥仅保留在当前进程和侧边栏控件中。")

    return llm_input or env_llm, tavily_input or env_tavily


def _render_history(history: list[dict[str, str]]) -> None:
    for item in history:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(content)


def _process_claim(
    claim: str,
    session: LearningSession,
    llm_key: str,
    tavily_key: str,
) -> tuple[object, object, str]:
    with _temporary_env({LLM_ENV: llm_key, TAVILY_ENV: tavily_key}):
        diagnosis_result = diagnose(claim)
        parsed = diagnosis_result.get("parsed")
        if not diagnosis_result.get("parse_ok") or not isinstance(parsed, dict):
            detail = diagnosis_result.get("parse_error") or "未返回可解析的 JSON"
            raise RuntimeError(f"诊断结果解析失败：{detail}")

        parsed, coverage_repairs = repair_diagnosis_coverage(
            parsed, load_json(DEFAULT_CARD_PATH)
        )
        if coverage_repairs:
            print(
                "[app_v3_demo] diagnosis coverage repaired: "
                + "；".join(coverage_repairs),
                file=sys.stderr,
            )

        state_result = session.submit(parsed)
        feedback_result = generate_feedback_v3(
            claim,
            parsed,
            DEFAULT_CARD_PATH,
            log=False,
        )
        search_notice = str(diagnosis_result.get("search_notice") or "").strip()
    return state_result, feedback_result, search_notice


def main() -> None:
    try:
        llm_key, tavily_key = _render_sidebar()

        st.title("新媒体广告前沿 - 概念学习闭环")
        st.info("请用你自己的话解释：议程设置（Agenda-Setting）")

        if not llm_key or not tavily_key:
            st.warning("请先在侧边栏配置 LLM 和 Tavily 的 API Key")
            return

        if "learning_session" not in st.session_state:
            st.session_state["learning_session"] = LearningSession(CONCEPT_SLUG)
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        session: LearningSession = st.session_state["learning_session"]
        history: list[dict[str, str]] = st.session_state["chat_history"]

        ui_error = st.session_state.get("ui_error")
        if ui_error:
            st.error(ui_error)

        _render_history(history)

        if session.status == PASS:
            st.success("🎉 恭喜你，通关！")
            return

        claim = st.chat_input("在这里输入你的理解...")
        if claim is None:
            return

        claim = str(claim).strip()
        if not claim:
            st.warning("请先输入你的理解。")
            return

        st.session_state.pop("ui_error", None)
        history.append({"role": "user", "content": claim})

        try:
            with st.spinner("AI 正在逐点诊断中..."):
                _, feedback_result, search_notice = _process_claim(
                    claim,
                    session,
                    llm_key,
                    tavily_key,
                )

            feedback_text = str(feedback_result.text).strip()
            if search_notice:
                feedback_text = search_notice + "\n\n" + feedback_text
            history.append(
                {"role": "assistant", "content": feedback_text}
            )
            if getattr(feedback_result, "degraded", False):
                detail = getattr(feedback_result, "error", "") or "未知原因"
                st.session_state["ui_error"] = (
                    "反馈生成失败，已展示兜底反馈："
                    + _redact(detail, (llm_key, tavily_key))
                )
        except Exception as exc:
            st.session_state["ui_error"] = (
                f"处理失败（{type(exc).__name__}）："
                + _redact(exc, (llm_key, tavily_key))
            )

        st.rerun()
    except Exception as exc:
        st.error(f"页面运行异常（{type(exc).__name__}）：{_redact(exc)}")


main()
