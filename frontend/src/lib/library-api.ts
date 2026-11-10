import {
  authHeaders,
  errorDetailFromPayload,
  notifyAuthRequired,
  notifyQuotaExceeded,
  quotaDetailFromPayload,
} from "@/lib/auth";

export interface ChapterTermRef {
  term_id: string;
  name: string;
}

export interface LibraryChapter {
  chapter_id: string;
  title: string;
  order: number;
  term_count: number;
  terms: ChapterTermRef[];
}

export interface LibraryBook {
  book_id: string;
  title: string;
  subject: string;
  chapter_count: number;
  term_count: number;
  chapters: LibraryChapter[];
}

export interface ScopeTerm {
  term_id: string;
  name: string;
  definition: string;
  key_points: string[];
  common_confusions: string[];
  book_id: string;
  book_title: string;
  chapter_id: string;
  chapter_title: string;
}

export interface ScopeSelection {
  book_ids: string[];
  chapter_ids: string[];
  chapter_count: number;
  term_count: number;
  summary: string;
  terms: ScopeTerm[];
  books: Array<{
    book_id: string;
    title: string;
    subject: string;
    chapters: Array<{ chapter_id: string; title: string; order: number }>;
  }>;
}

export type QuestionType = "choice" | "short_answer" | "flashcard";

export interface ReviewQuestion {
  question_id: string;
  type: QuestionType;
  question: string;
  options: string[];
  reference_excerpt: string;
  term_id: string;
  term_name: string;
  book_id: string;
  book_title: string;
  chapter_id: string;
  chapter_title: string;
}

export interface GenerateResult {
  questions: ReviewQuestion[];
  question_count: number;
  types: QuestionType[];
  scope: {
    book_ids: string[];
    chapter_ids: string[];
    chapter_count: number;
    term_count: number;
    summary: string;
  };
}

export interface GradeResult {
  correct: boolean;
  score: number;
  reference_excerpt: string;
  grading_reason: string;
  missing_points: string[];
  common_confusion: string | null;
  covered_points: string[];
  correct_answer: string;
  question_id: string | null;
  question_type: QuestionType;
  term_id: string;
  term_name: string;
  book_id: string;
  book_title: string;
  chapter_id: string;
  chapter_title: string;
  question: string;
  options: string[];
  key_points: Array<{ text: string; keywords?: string[] }>;
  common_confusions: string[];
  recorded_mistake_id: string | null;
}

export interface Mistake {
  id: string;
  book_id: string;
  chapter_id: string;
  term_id: string;
  term_name: string;
  book_title: string;
  chapter_title: string;
  question: string;
  question_type: QuestionType;
  user_answer: string;
  correct_answer: string;
  reason: string;
  missing_points: string[];
  created_at: string;
  next_review_at: string;
  review_count: number;
  question_id: string;
  options: string[];
  reference_excerpt: string;
  key_points: Array<{ text: string; keywords?: string[] }>;
  common_confusions: string[];
  last_reviewed_at?: string;
  last_review_result?: string;
}

export interface HintResult {
  term_id: string;
  term_name: string;
  definition: string;
  key_points: string[];
  common_confusion: string | null;
  suggested_review: string;
  scope_summary: string;
}

export interface TimelineItem {
  book_id: string;
  book_title: string;
  year: string;
  title: string;
  scholars: string;
  summary: string;
  points: string[];
  image: string;
  imageAlt: string;
  sort_year: number;
}

export interface HotCaseResult {
  term_id: string;
  term_name: string;
  case_summary: string;
  source_urls: string[];
  search_used: boolean;
  cached: boolean;
  notice: string;
  ai_unverified: true;
  warning: string;
  not_for_grading: true;
  fetched_at: string;
}

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");
const TIMEOUT_MS = 30_000;
export const SELECTION_STORAGE_KEY = "kb:selected-scope:v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: authHeaders({
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      }),
      signal: controller.signal,
    });
    const raw = await response.text();
    let payload: unknown = null;
    if (raw) {
      try {
        payload = JSON.parse(raw);
      } catch {
        throw new Error("后端返回了无法解析的数据。");
      }
    }
    if (!response.ok) {
      const detail = errorDetailFromPayload(
        payload,
        `请求失败（HTTP ${response.status}）`,
      );
      if (response.status === 401) {
        notifyAuthRequired({ message: detail });
      } else if (response.status === 429) {
        notifyQuotaExceeded(quotaDetailFromPayload(payload, detail));
      }
      throw new Error(detail);
    }
    return payload as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("请求超时，请确认后端服务正常。");
    }
    throw error instanceof Error ? error : new Error("网络请求失败。");
  } finally {
    clearTimeout(timeout);
  }
}

export async function getBooks(): Promise<LibraryBook[]> {
  const data = await request<{ books: LibraryBook[] }>("/library/books");
  return data.books ?? [];
}

export async function getChapters(bookId: string): Promise<LibraryBook> {
  return request<LibraryBook>(
    `/library/chapters?book_id=${encodeURIComponent(bookId)}`,
  );
}

export async function getSelection(
  bookIds: string[],
  chapterIds: string[],
): Promise<ScopeSelection> {
  return request<ScopeSelection>("/library/selection", {
    method: "POST",
    body: JSON.stringify({ book_ids: bookIds, chapter_ids: chapterIds }),
  });
}

export async function getTimeline(bookIds?: string[]): Promise<TimelineItem[]> {
  const suffix = bookIds?.length ? `?book_ids=${encodeURIComponent(bookIds.join(","))}` : "";
  const data = await request<{ items: TimelineItem[] }>(`/library/timeline${suffix}`);
  return data.items ?? [];
}

export async function generateQuestions(
  bookIds: string[],
  chapterIds: string[],
  types: QuestionType[],
  count: number,
): Promise<GenerateResult> {
  return request<GenerateResult>("/review/generate", {
    method: "POST",
    body: JSON.stringify({
      book_ids: bookIds,
      chapter_ids: chapterIds,
      types,
      count,
    }),
  });
}

export async function gradeQuestion(
  questionId: string,
  userAnswer: string,
): Promise<GradeResult> {
  return request<GradeResult>("/review/grade", {
    method: "POST",
    body: JSON.stringify({ question_id: questionId, user_answer: userAnswer }),
  });
}

export async function getMistakes(): Promise<{
  mistakes: Mistake[];
  count: number;
  stats: { total: number; due: number; reviewing: number };
}> {
  return request("/mistakes");
}

export async function getDueMistakes(): Promise<{
  mistakes: Mistake[];
  count: number;
}> {
  return request("/mistakes/due");
}

export async function reviewMistake(
  mistakeId: string,
  userAnswer: string,
): Promise<{ mistake: Mistake; grade: GradeResult | null; correct: boolean }> {
  return request(`/mistakes/${encodeURIComponent(mistakeId)}/review`, {
    method: "POST",
    body: JSON.stringify({ user_answer: userAnswer }),
  });
}

export async function getHint(input: {
  book_ids: string[];
  chapter_ids: string[];
  term_id: string;
  missing_points: string[];
}): Promise<HintResult> {
  return request("/review/hint", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getHotCase(termId: string, force = false): Promise<HotCaseResult> {
  return request("/case/hot", {
    method: "POST",
    body: JSON.stringify({ term_id: termId, force }),
  });
}

export interface StoredScope {
  book_ids: string[];
  chapter_ids: string[];
  summary: string;
  term_count: number;
}

export function storeSelection(scope: StoredScope): void {
  try {
    window.localStorage.setItem(SELECTION_STORAGE_KEY, JSON.stringify(scope));
  } catch {
    // Private mode or storage disabled: the library remains usable for this visit.
  }
}

export function readSelection(): StoredScope | null {
  try {
    const raw = window.localStorage.getItem(SELECTION_STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<StoredScope>;
    if (
      !Array.isArray(value.book_ids) ||
      !Array.isArray(value.chapter_ids) ||
      value.book_ids.length === 0 ||
      value.chapter_ids.length === 0
    ) {
      return null;
    }
    return {
      book_ids: value.book_ids.filter((item): item is string => typeof item === "string"),
      chapter_ids: value.chapter_ids.filter((item): item is string => typeof item === "string"),
      summary: typeof value.summary === "string" ? value.summary : "",
      term_count: typeof value.term_count === "number" ? value.term_count : 0,
    };
  } catch {
    return null;
  }
}

export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "未安排";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
