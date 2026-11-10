#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Admin-curated library, review loop and mistake-book HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from hot_case_service import search_hot_cases
from mistake_store import (
    add_mistake,
    get_mistake,
    list_due_mistakes,
    list_mistakes,
    mistake_stats,
    review_mistake,
)
from review_service import (
    build_hint,
    build_scope,
    build_timeline,
    chapters_for_book,
    books_metadata,
    find_term,
    generate_questions,
    grade_question,
    load_books,
)

router = APIRouter(tags=["library-review"])


class SelectionRequest(BaseModel):
    book_ids: list[str] = Field(default_factory=list)
    chapter_ids: list[str] = Field(default_factory=list)


class GenerateRequest(SelectionRequest):
    types: list[str] = Field(default_factory=lambda: ["choice", "short_answer"])
    count: int = Field(default=6, ge=1, le=20)


class GradeRequest(BaseModel):
    question_id: str | None = None
    mistake_id: str | None = None
    user_answer: str = Field(default="", max_length=4000)
    fallback_question: dict[str, Any] | None = None


class HintRequest(SelectionRequest):
    term_id: str | None = None
    missing_points: list[str] = Field(default_factory=list)


class ReviewMistakeRequest(BaseModel):
    user_answer: str | None = Field(default=None, max_length=4000)
    correct: bool | None = None


class HotCaseRequest(BaseModel):
    term_id: str | None = None
    term: str | None = None
    force: bool = False


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _public_scope(scope: dict[str, Any]) -> dict[str, Any]:
    result = dict(scope)
    result.pop("_terms_full", None)
    return result


def _resolve_term(term_id: str | None = None, term: str | None = None) -> dict[str, Any]:
    if term_id:
        found = find_term(term_id.strip())
        if found:
            return found
        raise HTTPException(status_code=404, detail=f"未找到术语：{term_id}")
    needle = str(term or "").strip().lower()
    if not needle:
        raise HTTPException(status_code=422, detail="term_id 或 term 至少提供一个")
    for book in load_books():
        for chapter in book["chapters"]:
            for item in chapter["terms"]:
                if item["name"].lower() == needle or needle in item["name"].lower():
                    return item
    raise HTTPException(status_code=404, detail=f"未找到与「{term}」匹配的术语")


@router.get("/library/books")
def api_library_books() -> dict[str, Any]:
    books = books_metadata()
    return {"books": books, "count": len(books)}


@router.get("/library/chapters")
def api_library_chapters(book_id: str = Query(..., min_length=1)) -> dict[str, Any]:
    try:
        return chapters_for_book(book_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/library/selection")
def api_library_selection(payload: SelectionRequest) -> dict[str, Any]:
    try:
        return _public_scope(build_scope(payload.book_ids, payload.chapter_ids))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/library/timeline")
def api_library_timeline(book_ids: str | None = Query(default=None)) -> dict[str, Any]:
    selected = [item.strip() for item in (book_ids or "").split(",") if item.strip()]
    items = build_timeline(selected or None)
    return {"items": items, "count": len(items), "book_ids": selected}


@router.post("/review/generate")
def api_review_generate(payload: GenerateRequest) -> dict[str, Any]:
    try:
        return generate_questions(
            payload.book_ids,
            payload.chapter_ids,
            payload.types,
            payload.count,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/review/grade")
def api_review_grade(payload: GradeRequest) -> dict[str, Any]:
    try:
        result = grade_question(
            payload.user_answer,
            question_id=payload.question_id,
            mistake_id=payload.mistake_id,
            fallback_question=payload.fallback_question,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc

    recorded_id = None
    if not result.get("correct"):
        question = {
            "question_id": result.get("question_id"),
            "type": result.get("question_type"),
            "question": result.get("question"),
            "options": result.get("options") or [],
            "reference_excerpt": result.get("reference_excerpt"),
            "term_id": result.get("term_id"),
            "term_name": result.get("term_name"),
            "book_id": result.get("book_id"),
            "book_title": result.get("book_title"),
            "chapter_id": result.get("chapter_id"),
            "chapter_title": result.get("chapter_title"),
            "correct_answer": result.get("correct_answer"),
            "key_points": result.get("key_points") or [],
            "common_confusions": result.get("common_confusions") or [],
            "option_term_map": result.get("option_term_map") or {},
        }
        recorded = add_mistake(question, result, payload.user_answer)
        recorded_id = recorded.get("id")
    return {**result, "recorded_mistake_id": recorded_id}


@router.get("/mistakes")
def api_mistakes() -> dict[str, Any]:
    items = list_mistakes()
    return {"mistakes": items, "count": len(items), "stats": mistake_stats()}


@router.get("/mistakes/due")
def api_due_mistakes() -> dict[str, Any]:
    items = list_due_mistakes()
    return {"mistakes": items, "count": len(items)}


@router.post("/mistakes/{mistake_id}/review")
def api_review_mistake(mistake_id: str, payload: ReviewMistakeRequest) -> dict[str, Any]:
    mistake = get_mistake(mistake_id)
    if not mistake:
        raise HTTPException(status_code=404, detail="错题不存在")

    grade = None
    if payload.user_answer is not None:
        try:
            grade = grade_question(payload.user_answer, mistake_id=mistake_id)
        except ValueError as exc:
            raise _bad_request(exc) from exc
        correct = bool(grade.get("correct"))
    elif payload.correct is not None:
        correct = bool(payload.correct)
    else:
        raise HTTPException(status_code=422, detail="user_answer 或 correct 至少提供一个")

    updated = review_mistake(mistake_id, correct)
    if updated is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    return {"mistake": updated, "grade": grade, "correct": correct}


@router.post("/review/hint")
def api_review_hint(payload: HintRequest) -> dict[str, Any]:
    try:
        return build_hint(
            payload.book_ids,
            payload.chapter_ids,
            term_id=payload.term_id,
            missing_points=payload.missing_points,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/case/hot")
def api_hot_case(payload: HotCaseRequest, request: Request) -> dict[str, Any]:
    term = _resolve_term(payload.term_id, payload.term)
    user_token = str(getattr(request.state, "user_token", "") or "").strip()
    return search_hot_cases(term, force=payload.force, quota_token=user_token)
