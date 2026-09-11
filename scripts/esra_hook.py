#!/usr/bin/env python3
"""Codex hook adapter for the local ESRA runtime."""

from __future__ import annotations

import json
import sys

from esra_runtime import data_dir, record_hook


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return 0
        record_hook(payload, data_dir())
    except Exception as exc:  # Hooks must never block the user's task.
        print(f"ESRA hook skipped: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
