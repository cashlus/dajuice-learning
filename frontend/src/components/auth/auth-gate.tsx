"use client";

import {
  useEffect,
  useState,
  useSyncExternalStore,
  type FormEvent,
  type ReactNode,
} from "react";
import { AlertTriangle, KeyRound, Loader2, LogOut, ShieldCheck } from "lucide-react";

import { DaJuiceLogo } from "@/components/y2k/dajuice-logo";
import { Y2KBackground } from "@/components/y2k/y2k-background";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { verifyUserToken } from "@/lib/api";
import {
  AUTH_REQUIRED_EVENT,
  QUOTA_EXCEEDED_EVENT,
  clearUserToken,
  getUserToken,
  setUserToken,
  subscribeUserToken,
  type AuthRequiredDetail,
  type QuotaExceededDetail,
} from "@/lib/auth";

interface AuthGateProps {
  children: ReactNode;
}

const emptySubscribe = () => () => {};

export function AuthGate({ children }: AuthGateProps) {
  const token = useSyncExternalStore(
    subscribeUserToken,
    getUserToken,
    () => null,
  );
  const hydrated = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
  const [draftToken, setDraftToken] = useState("");
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [quota, setQuota] = useState<QuotaExceededDetail | null>(null);

  useEffect(() => {
    const handleAuthRequired = (event: Event) => {
      const detail = (event as CustomEvent<AuthRequiredDetail>).detail;
      setDraftToken("");
      setAuthMessage(
        detail?.message || "登录状态已失效，请重新输入管理员发放的 Token。",
      );
    };

    const handleQuotaExceeded = (event: Event) => {
      const detail = (event as CustomEvent<QuotaExceededDetail>).detail;
      setQuota(detail ?? { message: "免费额度已用完，请稍后再试。" });
    };

    window.addEventListener(AUTH_REQUIRED_EVENT, handleAuthRequired);
    window.addEventListener(QUOTA_EXCEEDED_EVENT, handleQuotaExceeded);
    return () => {
      window.removeEventListener(AUTH_REQUIRED_EVENT, handleAuthRequired);
      window.removeEventListener(QUOTA_EXCEEDED_EVENT, handleQuotaExceeded);
    };
  }, []);

  async function handleActivate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const candidate = draftToken.trim();
    if (!candidate) {
      setFormError("请输入管理员发放的 User_Token。");
      return;
    }

    setIsChecking(true);
    setFormError(null);
    try {
      await verifyUserToken(candidate);
      setUserToken(candidate);
      setDraftToken("");
      setAuthMessage(null);
    } catch (error) {
      setFormError(
        error instanceof Error
          ? error.message
          : "暂时无法验证 Token，请检查网络或后端服务。",
      );
    } finally {
      setIsChecking(false);
    }
  }

  function handleSwitchToken() {
    clearUserToken();
    setDraftToken("");
    setAuthMessage("已退出当前 Token，请输入新的 User_Token。");
  }

  if (!hydrated) {
    return (
      <div className="y2k-page relative flex min-h-dvh items-center justify-center overflow-hidden">
        <Y2KBackground />
        <div className="relative z-10 flex items-center gap-3 font-pixel text-[9px] tracking-[0.18em] text-cyan-200">
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          BOOTING TERMINAL
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="y2k-page relative flex min-h-dvh items-center justify-center overflow-x-hidden px-4 py-10">
        <Y2KBackground />
        <main className="relative z-10 w-full max-w-lg">
          <div className="mb-7 text-center">
            <DaJuiceLogo className="justify-center" />
            <p className="mt-4 font-terminal text-sm tracking-[0.26em] text-cyan-200/70 uppercase">
              PRIVATE LEARNING TERMINAL
            </p>
          </div>

          <section className="y2k-panel relative overflow-hidden rounded-[2rem] p-6 sm:p-8">
            <div
              className="absolute -right-12 -top-14 size-40 rounded-full bg-fuchsia-500/15 blur-3xl"
              aria-hidden="true"
            />
            <div className="relative">
              <div className="flex size-13 items-center justify-center rounded-2xl border-2 border-cyan-200/30 bg-cyan-300/10 text-cyan-100 shadow-[0_0_28px_rgba(61,231,255,0.16)]">
                <ShieldCheck className="size-6" aria-hidden="true" />
              </div>
              <p className="y2k-kicker mt-6">
                <KeyRound className="size-3" aria-hidden="true" />
                ACCESS TOKEN REQUIRED
              </p>
              <h1 className="mt-4 text-3xl font-black leading-tight tracking-tight text-white sm:text-4xl">
                激活你的学习终端
              </h1>
              <p className="mt-3 text-sm leading-7 text-slate-400">
                输入管理员发放的 User_Token。模型与联网检索的 Key 只保存在服务器端，浏览器不会接触它们。
              </p>

              {authMessage ? (
                <div className="mt-5 flex items-start gap-2 rounded-xl border border-amber-300/25 bg-amber-300/[0.06] p-3 text-xs leading-5 text-amber-100/85">
                  <AlertTriangle
                    className="mt-0.5 size-4 shrink-0"
                    aria-hidden="true"
                  />
                  <span>{authMessage}</span>
                </div>
              ) : null}

              <form onSubmit={handleActivate} className="mt-6 space-y-3">
                <Input
                  type="password"
                  value={draftToken}
                  onChange={(event) => setDraftToken(event.target.value)}
                  placeholder="USER_TOKEN"
                  autoComplete="off"
                  spellCheck={false}
                  aria-label="User Token"
                  className="h-12 rounded-xl border-cyan-200/20 bg-black/35 px-4 font-mono text-sm tracking-wider text-cyan-50 placeholder:text-slate-600 focus-visible:border-fuchsia-300/50"
                />
                {formError ? (
                  <p className="rounded-lg border border-rose-300/20 bg-rose-400/[0.06] px-3 py-2 text-xs leading-5 text-rose-200">
                    {formError}
                  </p>
                ) : null}
                <Button
                  type="submit"
                  disabled={isChecking}
                  className="y2k-primary h-12 w-full gap-2 rounded-xl font-bold"
                >
                  {isChecking ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <KeyRound className="size-4" aria-hidden="true" />
                  )}
                  {isChecking ? "正在验证…" : "进入 DaJuice"}
                </Button>
              </form>

              <p className="mt-5 text-[11px] leading-5 text-slate-500">
                Token 仅保存在本机浏览器。若额度用完，可联系管理员获取新的 Token。
              </p>
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <>
      {children}
      <button
        type="button"
        onClick={handleSwitchToken}
        className="fixed bottom-4 left-4 z-40 inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-[#0b0712]/80 px-3 py-2 font-terminal text-xs tracking-[0.16em] text-slate-400 shadow-lg backdrop-blur-xl transition hover:border-cyan-300/25 hover:text-cyan-100"
        aria-label="切换 User Token"
      >
        <LogOut className="size-3.5" aria-hidden="true" />
        TOKEN
      </button>

      {quota ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 px-4 backdrop-blur-md"
          role="dialog"
          aria-modal="true"
          aria-labelledby="quota-title"
        >
          <section className="y2k-panel w-full max-w-md rounded-[1.75rem] border-amber-300/25 p-6 shadow-[0_0_60px_rgba(251,191,36,0.12)]">
            <div className="flex size-12 items-center justify-center rounded-xl border-2 border-amber-300/30 bg-amber-300/10 text-amber-200">
              <AlertTriangle className="size-5" aria-hidden="true" />
            </div>
            <h2 id="quota-title" className="mt-5 text-xl font-black text-white">
              免费额度已用完
            </h2>
            <p className="mt-3 text-sm leading-7 text-slate-300">{quota.message}</p>
            {quota.retryAfter && quota.retryAfter > 0 ? (
              <p className="mt-2 font-terminal text-xs tracking-[0.12em] text-slate-500">
                RETRY-AFTER ≈ {Math.max(1, Math.ceil(quota.retryAfter / 60))} MIN
              </p>
            ) : null}
            <div className="mt-6 flex flex-col gap-2 sm:flex-row">
              <Button
                type="button"
                onClick={() => setQuota(null)}
                className="y2k-primary h-10 flex-1 rounded-xl font-bold"
              >
                知道了
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setQuota(null);
                  handleSwitchToken();
                }}
                variant="outline"
                className="h-10 flex-1 rounded-xl border-white/15 bg-white/[0.03] text-slate-200"
              >
                切换 Token
              </Button>
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
