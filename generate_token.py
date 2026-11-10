#!/usr/bin/env python3
"""Generate random User_Token values for the hosted API.

Examples:
    python generate_token.py
    python generate_token.py --count 5

The output is printed only. Save the values in your password manager and set
them in the server-side USER_TOKENS environment variable. Never put a User_Token
in a repository or in NEXT_PUBLIC_* frontend variables.
"""

from __future__ import annotations

import argparse
import secrets


def generate_token() -> str:
    return "dju_" + secrets.token_urlsafe(32)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate User_Token values")
    parser.add_argument("--count", type=int, default=1, help="number of tokens (1-100)")
    args = parser.parse_args()
    count = max(1, min(100, args.count))
    for _ in range(count):
        print(generate_token())


if __name__ == "__main__":
    main()
