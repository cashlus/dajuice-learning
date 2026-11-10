#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Admin-curated library, scope selection, question generation and grading.

Only content loaded from v2/library/*.json is used as the authoritative
reference for questions and grading. No web search result is ever accepted as
a grading source.
"""

from __future__ import annotations

import json
import random
import re
import uuid
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

ROOT_DIR = Path(__file__).resolve().parent.parent
LIBRARY_DIR = ROOT_DIR / "v2" / "library"

VALID_QUESTION_TYPES = ("choice", "short_answer", "flashcard")
DEFAULT_QUESTION_TYPES = ("choice", "short_answer")
QUESTION_STORE_LIMIT = 800

_QUESTION_STORE: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_QUESTION_LOCK = Lock()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"知识库顶层必须是对象：{path.name}")
    return value


def _normalize_key_points(raw_points: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(raw_points, list):
        return result
    for item in raw_points:
        if isinstance(item, str):
            text = item.strip()
            keywords: list[str] = []
        elif isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            keywords = [
                str(keyword).strip()
                for keyword in (item.get("keywords") or [])
                if str(keyword).strip()
            ]
        else:
            continue
        if not text:
            continue
        if not keywords:
            keywords = [part for part in re.split(r"[，。；、：:（）()]", text) if len(part) >= 2]
        result.append({"text": text, "keywords": keywords})
    return result


def _normalize_terms(raw_terms: Any, book: dict[str, Any], chapter: dict[str, Any]) -> list[dict[str, Any]]:
    terms: list[dict[str, Any]] = []
    if not isinstance(raw_terms, list):
        return terms
    for item in raw_terms:
        if not isinstance(item, dict):
            continue
        term_id = str(item.get("term_id") or "").strip()
        name = str(item.get("name") or "").strip()
        definition = str(item.get("definition") or "").strip()
        if not term_id or not name or not definition:
            continue
        terms.append(
            {
                "term_id": term_id,
                "name": name,
                "definition": definition,
                "key_points": _normalize_key_points(item.get("key_points")),
                "common_confusions": [
                    str(value).strip()
                    for value in (item.get("common_confusions") or [])
                    if str(value).strip()
                ],
                "book_id": str(book.get("book_id") or ""),
                "book_title": str(book.get("title") or ""),
                "book_subject": str(book.get("subject") or ""),
                "chapter_id": str(chapter.get("chapter_id") or ""),
                "chapter_title": str(chapter.get("title") or ""),
                "chapter_order": int(chapter.get("order") or 0),
            }
        )
    return terms


def load_books() -> list[dict[str, Any]]:
    """Load all admin-curated books. Bad files fail loudly for admins."""
    books: list[dict[str, Any]] = []
    if not LIBRARY_DIR.exists():
        return books
    for path in sorted(LIBRARY_DIR.glob("*.json")):
        data = _read_json(path)
        book_id = str(data.get("book_id") or "").strip()
        title = str(data.get("title") or "").strip()
        subject = str(data.get("subject") or "").strip()
        if not book_id or not title:
            raise ValueError(f"知识库缺少 book_id/title：{path.name}")

        chapters: list[dict[str, Any]] = []
        raw_chapters = data.get("chapters") or []
        if not isinstance(raw_chapters, list):
            raise ValueError(f"chapters 必须是数组：{path.name}")
        for raw_chapter in sorted(
            raw_chapters,
            key=lambda value: int(value.get("order") or 0) if isinstance(value, dict) else 0,
        ):
            if not isinstance(raw_chapter, dict):
                continue
            chapter = {
                "chapter_id": str(raw_chapter.get("chapter_id") or "").strip(),
                "title": str(raw_chapter.get("title") or "").strip(),
                "order": int(raw_chapter.get("order") or 0),
                "content": str(raw_chapter.get("content") or "").strip(),
            }
            if not chapter["chapter_id"] or not chapter["title"]:
                continue
            chapter["terms"] = _normalize_terms(raw_chapter.get("terms"), data, chapter)
            chapters.append(chapter)

        timeline: list[dict[str, Any]] = []
        for raw_item in data.get("timeline") or []:
            if not isinstance(raw_item, dict):
                continue
            timeline.append(
                {
                    "book_id": book_id,
                    "book_title": title,
                    "year": str(raw_item.get("year") or "").strip(),
                    "title": str(raw_item.get("title") or "").strip(),
                    "scholars": str(raw_item.get("scholars") or "").strip(),
                    "summary": str(raw_item.get("summary") or "").strip(),
                    "points": [
                        str(point).strip()
                        for point in (raw_item.get("points") or [])
                        if str(point).strip()
                    ],
                    "image": str(raw_item.get("image") or "").strip(),
                    "imageAlt": str(raw_item.get("imageAlt") or "").strip(),
                }
            )

        books.append(
            {
                "book_id": book_id,
                "title": title,
                "subject": subject,
                "chapters": chapters,
                "timeline": timeline,
            }
        )
    return books


def books_metadata() -> list[dict[str, Any]]:
    """Return chapter-tree metadata without long chapter content."""
    result: list[dict[str, Any]] = []
    for book in load_books():
        chapters = []
        for chapter in book["chapters"]:
            chapters.append(
                {
                    "chapter_id": chapter["chapter_id"],
                    "title": chapter["title"],
                    "order": chapter["order"],
                    "term_count": len(chapter["terms"]),
                    "terms": [
                        {"term_id": term["term_id"], "name": term["name"]}
                        for term in chapter["terms"]
                    ],
                }
            )
        result.append(
            {
                "book_id": book["book_id"],
                "title": book["title"],
                "subject": book["subject"],
                "chapter_count": len(chapters),
                "term_count": sum(chapter["term_count"] for chapter in chapters),
                "chapters": chapters,
            }
        )
    return result


def chapters_for_book(book_id: str) -> dict[str, Any]:
    for book in load_books():
        if book["book_id"] != book_id:
            continue
        return {
            "book_id": book["book_id"],
            "title": book["title"],
            "subject": book["subject"],
            "chapters": [
                {
                    "chapter_id": chapter["chapter_id"],
                    "title": chapter["title"],
                    "order": chapter["order"],
                    "term_count": len(chapter["terms"]),
                    "terms": [
                        {"term_id": term["term_id"], "name": term["name"]}
                        for term in chapter["terms"]
                    ],
                }
                for chapter in book["chapters"]
            ],
        }
    raise ValueError(f"未找到教材：{book_id}")


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def build_scope(book_ids: Iterable[str], chapter_ids: Iterable[str]) -> dict[str, Any]:
    selected_book_ids = _unique(book_ids)
    requested_chapter_ids = _unique(chapter_ids)
    if not selected_book_ids:
        raise ValueError("请至少选择一本教材。")
    if not requested_chapter_ids:
        raise ValueError("请至少选择一个章节。")

    books = load_books()
    books_by_id = {book["book_id"]: book for book in books}
    unknown_books = [book_id for book_id in selected_book_ids if book_id not in books_by_id]
    if unknown_books:
        raise ValueError("未找到教材：" + "、".join(unknown_books))

    requested = set(requested_chapter_ids)
    found: set[str] = set()
    selected_books: list[dict[str, Any]] = []
    terms: list[dict[str, Any]] = []

    for book_id in selected_book_ids:
        book = books_by_id[book_id]
        selected_chapters: list[dict[str, Any]] = []
        for chapter in book["chapters"]:
            if chapter["chapter_id"] not in requested:
                continue
            found.add(chapter["chapter_id"])
            selected_chapters.append(chapter)
            terms.extend(chapter["terms"])
        if selected_chapters:
            selected_books.append(
                {
                    "book_id": book["book_id"],
                    "title": book["title"],
                    "subject": book["subject"],
                    "chapters": [
                        {
                            "chapter_id": chapter["chapter_id"],
                            "title": chapter["title"],
                            "order": chapter["order"],
                        }
                        for chapter in selected_chapters
                    ],
                }
            )

    missing = sorted(requested - found)
    if missing:
        raise ValueError("以下章节不属于已选教材或不存在：" + "、".join(missing))
    if not terms:
        raise ValueError("所选范围没有可用术语。")

    term_summaries = [
        {
            "term_id": term["term_id"],
            "name": term["name"],
            "definition": term["definition"],
            "key_points": [point["text"] for point in term["key_points"]],
            "common_confusions": term["common_confusions"],
            "book_id": term["book_id"],
            "book_title": term["book_title"],
            "chapter_id": term["chapter_id"],
            "chapter_title": term["chapter_title"],
        }
        for term in terms
    ]
    return {
        "book_ids": selected_book_ids,
        "chapter_ids": requested_chapter_ids,
        "books": selected_books,
        "chapter_count": len(found),
        "term_count": len(terms),
        "summary": f"已选择 {len(selected_books)} 本教材、{len(found)} 个章节、{len(terms)} 个术语。",
        "terms": term_summaries,
        "_terms_full": terms,
    }


def build_timeline(book_ids: Iterable[str] | None = None) -> list[dict[str, Any]]:
    selected = set(_unique(book_ids or []))
    items: list[dict[str, Any]] = []
    for book in load_books():
        if selected and book["book_id"] not in selected:
            continue
        for item in book["timeline"]:
            enriched = dict(item)
            digits = re.search(r"\d{4}", item["year"])
            enriched["sort_year"] = int(digits.group(0)) if digits else 0
            items.append(enriched)
    items.sort(key=lambda item: (item["sort_year"], item["book_title"], item["title"]))
    return items


def _reference_excerpt(term: dict[str, Any]) -> str:
    points = "；".join(point["text"] for point in term["key_points"])
    if points:
        return f"{term['definition']}\n关键要点：{points}"
    return term["definition"]


def _public_question(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": question["question_id"],
        "type": question["type"],
        "question": question["question"],
        "options": list(question.get("options") or []),
        "reference_excerpt": question["reference_excerpt"],
        "term_id": question["term_id"],
        "term_name": question["term_name"],
        "book_id": question["book_id"],
        "book_title": question["book_title"],
        "chapter_id": question["chapter_id"],
        "chapter_title": question["chapter_title"],
    }


def _register_question(question: dict[str, Any]) -> dict[str, Any]:
    with _QUESTION_LOCK:
        _QUESTION_STORE[question["question_id"]] = question
        while len(_QUESTION_STORE) > QUESTION_STORE_LIMIT:
            _QUESTION_STORE.popitem(last=False)
    return _public_question(question)


def _make_choice(term: dict[str, Any], scope_terms: list[dict[str, Any]]) -> dict[str, Any] | None:
    other_terms = [other for other in scope_terms if other["term_id"] != term["term_id"]]
    if not other_terms:
        return None
    options = [term["definition"]] + [other["definition"] for other in other_terms[:3]]
    random.Random(term["term_id"]).shuffle(options)
    question_id = f"q-{uuid.uuid4().hex}"
    question = {
        "question_id": question_id,
        "type": "choice",
        "question": f"以下哪一项最准确地解释「{term['name']}」？",
        "options": options,
        "reference_excerpt": _reference_excerpt(term),
        "term_id": term["term_id"],
        "term_name": term["name"],
        "book_id": term["book_id"],
        "book_title": term["book_title"],
        "chapter_id": term["chapter_id"],
        "chapter_title": term["chapter_title"],
        "correct_answer": term["definition"],
        "key_points": term["key_points"],
        "common_confusions": term["common_confusions"],
        "option_term_map": {
            other["definition"]: other["name"]
            for other in other_terms[:3]
        },
    }
    return question


def _make_open_question(term: dict[str, Any], question_type: str) -> dict[str, Any]:
    label = "记忆卡片" if question_type == "flashcard" else "简答题"
    prompt = (
        f"{label}：请先回忆并写出「{term['name']}」的定义与关键特征。"
        if question_type == "flashcard"
        else f"请用自己的话解释「{term['name']}」，并说明它的关键特征。"
    )
    return {
        "question_id": f"q-{uuid.uuid4().hex}",
        "type": question_type,
        "question": prompt,
        "options": [],
        "reference_excerpt": _reference_excerpt(term),
        "term_id": term["term_id"],
        "term_name": term["name"],
        "book_id": term["book_id"],
        "book_title": term["book_title"],
        "chapter_id": term["chapter_id"],
        "chapter_title": term["chapter_title"],
        "correct_answer": _reference_excerpt(term),
        "key_points": term["key_points"],
        "common_confusions": term["common_confusions"],
        "option_term_map": {},
    }


def _normalize_types(raw_types: Iterable[str] | None) -> list[str]:
    values = _unique(raw_types or DEFAULT_QUESTION_TYPES)
    normalized: list[str] = []
    aliases = {
        "single_choice": "choice",
        "single-choice": "choice",
        "short": "short_answer",
        "short-answer": "short_answer",
        "card": "flashcard",
    }
    for value in values:
        key = aliases.get(value.lower(), value.lower())
        if key in VALID_QUESTION_TYPES and key not in normalized:
            normalized.append(key)
    return normalized or list(DEFAULT_QUESTION_TYPES)


def generate_questions(
    book_ids: Iterable[str],
    chapter_ids: Iterable[str],
    types: Iterable[str] | None = None,
    count: int = 6,
) -> dict[str, Any]:
    scope = build_scope(book_ids, chapter_ids)
    scope_terms = scope["_terms_full"]
    requested_types = _normalize_types(types)
    total = max(1, min(int(count or 6), 20))
    questions: list[dict[str, Any]] = []

    for term in scope_terms:
        for question_type in requested_types:
            if len(questions) >= total:
                break
            if question_type == "choice":
                raw_question = _make_choice(term, scope_terms)
                if raw_question is None:
                    continue
            else:
                raw_question = _make_open_question(term, question_type)
            questions.append(_register_question(raw_question))
        if len(questions) >= total:
            break

    if not questions and "choice" in requested_types:
        raise ValueError("当前范围至少需要两个术语才能生成选择题，请增加章节或改用简答题。")
    if not questions:
        raise ValueError("当前范围无法生成题目。")

    return {
        "questions": questions,
        "question_count": len(questions),
        "types": requested_types,
        "scope": {
            "book_ids": scope["book_ids"],
            "chapter_ids": scope["chapter_ids"],
            "chapter_count": scope["chapter_count"],
            "term_count": scope["term_count"],
            "summary": scope["summary"],
        },
    }


def _normalize_answer(value: str) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[\s，。！？；：、,.!?;:'\"“”‘’（）()【】《》\-—_/]", "", text)


def _contains_keyword(answer: str, keyword: str) -> bool:
    normalized = _normalize_answer(keyword)
    return bool(normalized) and normalized in answer


def _choice_selection(question: dict[str, Any], user_answer: str) -> str:
    options = question.get("options") or []
    raw = str(user_answer or "").strip()
    if not raw:
        return ""
    upper = raw.upper()
    if len(upper) == 1 and "A" <= upper <= "Z":
        index = ord(upper) - ord("A")
        if 0 <= index < len(options):
            return str(options[index])
    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(options):
            return str(options[index])
    normalized = _normalize_answer(raw)
    for option in options:
        if _normalize_answer(str(option)) == normalized:
            return str(option)
    return raw


def _grade_choice(question: dict[str, Any], user_answer: str) -> dict[str, Any]:
    selected = _choice_selection(question, user_answer)
    correct_answer = str(question["correct_answer"])
    correct = _normalize_answer(selected) == _normalize_answer(correct_answer)
    distractor_name = (question.get("option_term_map") or {}).get(selected)
    common_confusion = None
    if not correct and distractor_name:
        common_confusion = f"你选择的选项是「{distractor_name}」的定义，可能与「{question['term_name']}」混淆。"
    return {
        "correct": correct,
        "score": 100 if correct else 0,
        "reference_excerpt": question["reference_excerpt"],
        "grading_reason": (
            "你选择了与知识库定义一致的选项。"
            if correct
            else "你的选择与知识库定义不一致；请对照教材依据重新区分。"
        ),
        "missing_points": [] if correct else [point["text"] for point in question.get("key_points", [])],
        "common_confusion": common_confusion,
        "covered_points": [] if correct else [],
        "correct_answer": correct_answer,
    }


def _detect_common_confusion(term: dict[str, Any], answer: str) -> str | None:
    confusions = term.get("common_confusions") or []
    if not confusions:
        return None
    markers = ("直接决定", "告诉", "支持谁", "立场", "框架", "启动效应", "priming", "价格", "曝光")
    if any(marker in answer for marker in markers):
        return f"该术语的常见混淆是：{confusions[0]}"
    return None


def _grade_open(question: dict[str, Any], user_answer: str) -> dict[str, Any]:
    answer = _normalize_answer(user_answer)
    key_points = question.get("key_points") or []
    covered: list[str] = []
    missing: list[str] = []
    for point in key_points:
        keywords = point.get("keywords") or [point.get("text", "")]
        if any(_contains_keyword(answer, str(keyword)) for keyword in keywords):
            covered.append(point["text"])
        else:
            missing.append(point["text"])

    total = len(key_points)
    coverage = len(covered) / total if total else 0.0
    correct = bool(total) and coverage >= 1.0 and len(answer) >= 8
    score = round(coverage * 100)
    if len(answer) < 8:
        score = min(score, 30)
    if correct:
        score = 100

    common_confusion = None
    if not correct:
        common_confusion = _detect_common_confusion(question, user_answer)
    return {
        "correct": correct,
        "score": score,
        "reference_excerpt": question["reference_excerpt"],
        "grading_reason": (
            f"你覆盖了 {len(covered)}/{total} 个关键要点，表达长度达到要求。"
            if correct
            else f"你覆盖了 {len(covered)}/{total} 个关键要点，仍有 {len(missing)} 个要点没有说到。"
        ),
        "missing_points": missing,
        "common_confusion": common_confusion,
        "covered_points": covered,
        "correct_answer": question["correct_answer"],
    }


def _question_from_mistake(mistake: dict[str, Any]) -> dict[str, Any]:
    question_type = str(mistake.get("question_type") or "short_answer")
    key_points = mistake.get("key_points") or []
    if key_points and isinstance(key_points[0], str):
        key_points = [{"text": text, "keywords": [text]} for text in key_points]
    return {
        "question_id": str(mistake.get("question_id") or mistake.get("id")),
        "type": question_type,
        "question": str(mistake.get("question") or ""),
        "options": list(mistake.get("options") or []),
        "reference_excerpt": str(mistake.get("reference_excerpt") or mistake.get("correct_answer") or ""),
        "term_id": str(mistake.get("term_id") or ""),
        "term_name": str(mistake.get("term_name") or ""),
        "book_id": str(mistake.get("book_id") or ""),
        "book_title": str(mistake.get("book_title") or ""),
        "chapter_id": str(mistake.get("chapter_id") or ""),
        "chapter_title": str(mistake.get("chapter_title") or ""),
        "correct_answer": str(mistake.get("correct_answer") or ""),
        "key_points": key_points,
        "common_confusions": list(mistake.get("common_confusions") or []),
        "option_term_map": dict(mistake.get("option_term_map") or {}),
    }


def grade_question(
    user_answer: str,
    *,
    question_id: str | None = None,
    mistake_id: str | None = None,
    fallback_question: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question: dict[str, Any] | None = None
    if question_id:
        with _QUESTION_LOCK:
            question = _QUESTION_STORE.get(question_id)
    if question is None and mistake_id:
        from mistake_store import get_mistake

        mistake = get_mistake(mistake_id)
        if mistake:
            question = _question_from_mistake(mistake)
    if question is None and fallback_question:
        if not fallback_question.get("reference_excerpt"):
            raise ValueError("题目缺少知识库依据，不能判分。")
        question = dict(fallback_question)
    if question is None:
        raise ValueError("题目已过期，请重新生成题目。")

    question_type = str(question.get("type") or "short_answer")
    if question_type == "choice":
        result = _grade_choice(question, user_answer)
    else:
        result = _grade_open(question, user_answer)
    result["question_id"] = question.get("question_id")
    result["question_type"] = question_type
    result["term_id"] = question.get("term_id")
    result["term_name"] = question.get("term_name")
    result["book_id"] = question.get("book_id")
    result["book_title"] = question.get("book_title")
    result["chapter_id"] = question.get("chapter_id")
    result["chapter_title"] = question.get("chapter_title")
    result["question"] = question.get("question")
    result["options"] = list(question.get("options") or [])
    result["key_points"] = question.get("key_points") or []
    result["common_confusions"] = question.get("common_confusions") or []
    result["option_term_map"] = question.get("option_term_map") or {}
    return result


def build_hint(
    book_ids: Iterable[str],
    chapter_ids: Iterable[str],
    *,
    term_id: str | None = None,
    missing_points: Iterable[str] | None = None,
) -> dict[str, Any]:
    scope = build_scope(book_ids, chapter_ids)
    terms = scope["_terms_full"]
    term = next((item for item in terms if item["term_id"] == term_id), None) if term_id else None
    if term is None:
        term = terms[0]
    missing = [str(item).strip() for item in (missing_points or []) if str(item).strip()]
    suggested = "先复述定义，再补上：" + "；".join(missing) if missing else (
        "先复述定义，再用自己的话连接关键要点：" + "；".join(point["text"] for point in term["key_points"])
    )
    return {
        "term_id": term["term_id"],
        "term_name": term["name"],
        "definition": term["definition"],
        "key_points": [point["text"] for point in term["key_points"]],
        "common_confusion": "；".join(term["common_confusions"]) or None,
        "suggested_review": suggested,
        "scope_summary": scope["summary"],
    }


def find_term(term_id: str) -> dict[str, Any] | None:
    for book in load_books():
        for chapter in book["chapters"]:
            for term in chapter["terms"]:
                if term["term_id"] == term_id:
                    return term
    return None