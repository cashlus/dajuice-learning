#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tiny per-token quota manager backed by an in-process lock and JSON file."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_QUOTA_PATH = ROOT_DIR / "data" / "user_quota.json"
QuotaKind = Literal["diagnosis", "tavily"]
QuotaWindow = Literal["day", "month"]


class QuotaExceeded(Exception):
    """Raised before an expensive model or search call would exceed a quota."""

    def __init__(
        self,
        *,
        kind: QuotaKind,
        window: QuotaWindow,
        used: int,
        limit: int,
        retry_after: int,
    ) -> None:
        self.kind = kind
        self.window = window
        self.used = used
        self.limit = limit
        self.retry_after = retry_after
        label = "诊断" if kind == "diagnosis" else "联网检索"
        if window == "day":
            detail = f"今日免费{label}额度已用完（{used}/{limit}），请明天再来。"
        else:
            detail = f"本月免费{label}额度已用完（{used}/{limit}），请联系管理员充值。"
        super().__init__(detail)

    @property
    def detail(self) -> str:
        return str(self)


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _timezone_offset() -> timezone:
    try:
        hours = float(os.environ.get("QUOTA_TIMEZONE_OFFSET", "8"))
    except (TypeError, ValueError):
        hours = 8.0
    return timezone(timedelta(hours=hours))


class QuotaManager:
    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else None
        self._lock = threading.RLock()

    @property
    def path(self) -> Path:
        if self._path is not None:
            return self._path
        return Path(os.environ.get("QUOTA_PATH", str(DEFAULT_QUOTA_PATH)))

    def _now(self) -> datetime:
        return datetime.now(_timezone_offset())

    def _limits(self, kind: QuotaKind) -> dict[QuotaWindow, int]:
        if kind == "diagnosis":
            return {
                "day": _int_env("DAILY_DIAGNOSIS_LIMIT", 50),
                "month": _int_env("MONTHLY_DIAGNOSIS_LIMIT", 1000),
            }
        return {
            "day": _int_env("DAILY_TAVILY_LIMIT", 5),
            "month": _int_env("MONTHLY_TAVILY_LIMIT", 60),
        }

    @staticmethod
    def _token_key(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _load(self) -> dict[str, Any]:
        path = self.path
        if not path.exists():
            return {"version": 1, "tokens": {}}
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "tokens": {}}
        if not isinstance(value, dict) or not isinstance(value.get("tokens"), dict):
            return {"version": 1, "tokens": {}}
        return value

    def _save(self, value: dict[str, Any]) -> None:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp, path)

    def _record_for(self, data: dict[str, Any], token: str, now: datetime) -> dict[str, Any]:
        key = self._token_key(token)
        tokens = data.setdefault("tokens", {})
        record = tokens.get(key)
        if not isinstance(record, dict):
            record = {}
            tokens[key] = record

        record["fingerprint"] = key[:12]
        record["updated_at"] = now.isoformat(timespec="seconds")

        daily = record.get("daily")
        if not isinstance(daily, dict) or daily.get("date") != now.date().isoformat():
            record["daily"] = {
                "date": now.date().isoformat(),
                "diagnosis": 0,
                "tavily": 0,
            }

        monthly = record.get("monthly")
        month_key = now.strftime("%Y-%m")
        if not isinstance(monthly, dict) or monthly.get("month") != month_key:
            record["monthly"] = {
                "month": month_key,
                "diagnosis": 0,
                "tavily": 0,
            }
        return record

    def _retry_after(self, window: QuotaWindow, now: datetime) -> int:
        if window == "day":
            reset = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            if now.month == 12:
                reset = now.replace(
                    year=now.year + 1,
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            else:
                reset = now.replace(
                    month=now.month + 1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
        return max(60, int((reset - now).total_seconds()))

    def consume(self, user_token: str | None, kind: QuotaKind) -> dict[str, Any] | None:
        """Check and increment one unit before an LLM or Tavily request.

        CLI callers without a user token keep their previous behaviour. HTTP
        requests always carry a validated token and therefore always count.
        """
        token = str(user_token or "").strip()
        if not token:
            return None
        if kind not in ("diagnosis", "tavily"):
            raise ValueError(f"未知配额类型：{kind}")

        with self._lock:
            now = self._now()
            data = self._load()
            record = self._record_for(data, token, now)
            limits = self._limits(kind)

            for window, bucket_name in (("day", "daily"), ("month", "monthly")):
                bucket = record[bucket_name]
                used = int(bucket.get(kind, 0) or 0)
                limit = limits[window]
                if used >= limit:
                    raise QuotaExceeded(
                        kind=kind,
                        window=window,
                        used=used,
                        limit=limit,
                        retry_after=self._retry_after(window, now),
                    )

            record["daily"][kind] = int(record["daily"].get(kind, 0) or 0) + 1
            record["monthly"][kind] = int(record["monthly"].get(kind, 0) or 0) + 1
            record["updated_at"] = now.isoformat(timespec="seconds")
            self._save(data)
            return {
                "kind": kind,
                "daily_used": record["daily"][kind],
                "daily_limit": limits["day"],
                "monthly_used": record["monthly"][kind],
                "monthly_limit": limits["month"],
            }


quota_manager = QuotaManager()
