import {
  authHeaders,
  errorDetailFromPayload,
  notifyAuthRequired,
  notifyQuotaExceeded,
  quotaDetailFromPayload,
} from "@/lib/auth";

export type LearningStatus = "PASS" | "NEED_RETRY" | "NEED_RECONFIRM";

export interface DiagnoseResult {
  status: LearningStatus;
  feedback: string;
  missing_elements: string[];
  search_used: boolean;
  search_notice: string;
}

export interface ResetResult {
  status: "reset";
  session_id: string;
}

type ApiErrorCode = "NETWORK" | "TIMEOUT" | "HTTP" | "INVALID_RESPONSE";

interface ApiErrorOptions {
  code: ApiErrorCode;
  status?: number;
  cause?: unknown;
}

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status?: number;

  constructor(message: string, options: ApiErrorOptions) {
    super(message, { cause: options.cause });
    this.name = "ApiError";
    this.code = options.code;
    this.status = options.status;
  }
}

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const REQUEST_TIMEOUT_MS = 90_000;
const STATUSES: LearningStatus[] = ["PASS", "NEED_RETRY", "NEED_RECONFIRM"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isLearningStatus(value: unknown): value is LearningStatus {
  return typeof value === "string" && STATUSES.includes(value as LearningStatus);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function extractErrorDetail(payload: unknown, fallback: string): string {
  if (!isRecord(payload) || !("detail" in payload)) {
    return fallback;
  }

  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!isRecord(item)) {
          return "";
        }
        return typeof item.msg === "string" ? item.msg : "";
      })
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join("；");
    }
  }

  return fallback;
}

async function postJson(path: string, body: Record<string, unknown>): Promise<unknown> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: authHeaders({
        "Content-Type": "application/json",
        Accept: "application/json",
      }),
      body: JSON.stringify(body),
      cache: "no-store",
      signal: controller.signal,
    });

    const rawBody = await response.text();
    let payload: unknown = null;

    if (rawBody) {
      try {
        payload = JSON.parse(rawBody);
      } catch (error) {
        if (response.ok) {
          throw new ApiError("后端返回了无法解析的数据，请检查服务日志。", {
            code: "INVALID_RESPONSE",
            cause: error,
          });
        }
      }
    }

    if (!response.ok) {
      const detail = extractErrorDetail(
        payload,
        `请求失败（HTTP ${response.status}）`,
      );
      if (response.status === 401) {
        notifyAuthRequired({ message: detail });
      } else if (response.status === 429) {
        notifyQuotaExceeded(quotaDetailFromPayload(payload, detail));
      }
      throw new ApiError(
        detail,
        { code: "HTTP", status: response.status, cause: payload },
      );
    }

    return payload;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("诊断请求超时了，请稍后重试。", {
        code: "TIMEOUT",
        cause: error,
      });
    }

    throw new ApiError(
      `无法连接后端服务，请确认 ${API_BASE_URL} 已启动。`,
      { code: "NETWORK", cause: error },
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function diagnose(
  claim: string,
  sessionId: string,
): Promise<DiagnoseResult> {
  const payload = await postJson("/api/diagnose", {
    claim,
    session_id: sessionId,
  });

  if (!isRecord(payload) || !isLearningStatus(payload.status)) {
    throw new ApiError("诊断结果缺少有效的 status 字段。", {
      code: "INVALID_RESPONSE",
    });
  }

  if (typeof payload.feedback !== "string" || !payload.feedback.trim()) {
    throw new ApiError("诊断结果没有返回可展示的反馈内容。", {
      code: "INVALID_RESPONSE",
    });
  }

  if (!isStringArray(payload.missing_elements)) {
    throw new ApiError("诊断结果中的 missing_elements 格式不正确。", {
      code: "INVALID_RESPONSE",
    });
  }

  return {
    status: payload.status,
    feedback: payload.feedback,
    missing_elements: payload.missing_elements,
    search_used: payload.search_used === true,
    search_notice:
      typeof payload.search_notice === "string" ? payload.search_notice : "",
  };
}

export async function resetSession(sessionId: string): Promise<ResetResult> {
  const payload = await postJson("/api/reset", { session_id: sessionId });

  if (
    !isRecord(payload) ||
    payload.status !== "reset" ||
    typeof payload.session_id !== "string"
  ) {
    throw new ApiError("重置接口返回的数据结构不正确。", {
      code: "INVALID_RESPONSE",
    });
  }

  return {
    status: "reset",
    session_id: payload.session_id,
  };
}

export async function verifyUserToken(token: string): Promise<void> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 20_000);

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/check`, {
      headers: {
        Authorization: `Bearer ${token.trim()}`,
        Accept: "application/json",
      },
      cache: "no-store",
      signal: controller.signal,
    });

    const rawBody = await response.text();
    let payload: unknown = null;
    if (rawBody) {
      try {
        payload = JSON.parse(rawBody);
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      throw new ApiError(
        errorDetailFromPayload(
          payload,
          `Token 验证失败（HTTP ${response.status}）。`,
        ),
        { code: "HTTP", status: response.status, cause: payload },
      );
    }

    if (!isRecord(payload) || payload.ok !== true) {
      throw new ApiError("后端没有确认 Token 有效，请检查服务配置。", {
        code: "INVALID_RESPONSE",
        cause: payload,
      });
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        "Token 验证超时。Render 免费层可能在冷启动，请等约 50 秒后重试。",
        { code: "TIMEOUT", cause: error },
      );
    }
    throw new ApiError(
      `无法连接后端服务（${API_BASE_URL}），请确认 Render 服务已启动。`,
      { code: "NETWORK", cause: error },
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

export function getReadableError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "发生了未知错误，请稍后再试。";
}
