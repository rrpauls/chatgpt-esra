#!/usr/bin/env python3
"""Export local Codex ESRA records as portable ESRA 1.2 cycle events."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

IMPLEMENTATION = "chatgpt-esra"
SCHEMA_VERSION = "1.0.0"
PROTOCOL_VERSION = "1.2"
ROTATED_LOGS = ("events.1.jsonl", "events.jsonl.1", "events.jsonl")
PAYLOAD_FIELDS = {
    "task", "change", "verification", "uncertainty", "recommended",
    "recommend_cycle", "reason", "reasons", "score", "threshold", "mode",
    "experiment", "name", "decision", "metrics", "workspace", "event",
}


def resolve_data_dir(value: str | None) -> Path:
    raw = value or os.environ.get("ESRA_DATA_DIR") or os.environ.get("PLUGIN_DATA")
    return Path(raw).expanduser() if raw else Path.home() / ".codex" / "esra"


def normalize_timestamp(value: Any, fallback: float) -> str:
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed.isoformat(timespec="seconds")
        except ValueError:
            pass
    return datetime.fromtimestamp(fallback, timezone.utc).isoformat(timespec="seconds")


def event_type(kind: str) -> str:
    lowered = kind.lower()
    if "trigger" in lowered:
        return "trigger"
    if "experiment" in lowered:
        return "experiment"
    if "audit" in lowered or "validate" in lowered:
        return "audit"
    if lowered in {"lifecycle", "baseline", "observation"}:
        return "observation"
    return "integration"


def normalized_outcome(record: dict[str, Any], kind: str) -> str | None:
    raw = str(record.get("outcome", "")).lower()
    if raw in {"success", "failure", "partial", "inconclusive"}:
        return raw
    if raw == "blocked" or "blocked" in kind.lower():
        return "not-run"
    if raw == "abandoned":
        return "inconclusive"
    return None


def stable_id(record: dict[str, Any], source: str) -> str:
    existing = record.get("id") or record.get("run_id")
    if existing:
        return str(existing)
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{IMPLEMENTATION}|{source}|{canonical}".encode()).hexdigest()
    return digest[:32]


def normalize_evidence(record: dict[str, Any], source: str) -> list[str]:
    raw = record.get("evidence")
    if isinstance(raw, list):
        evidence = [str(item).strip() for item in raw if str(item).strip()]
    elif raw:
        evidence = [str(raw).strip()]
    else:
        evidence = []
    verification = str(record.get("verification", "")).strip()
    if verification and verification not in evidence:
        evidence.append(verification)
    evidence.append(f"source:{source}")
    return evidence


def normalize_record(record: dict[str, Any], source: str, fallback: float) -> dict[str, Any]:
    kind = str(record.get("kind") or record.get("event") or "unknown")
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "id": stable_id(record, source),
        "timestamp": normalize_timestamp(record.get("timestamp") or record.get("ts"), fallback),
        "implementation": IMPLEMENTATION,
        "event_type": event_type(kind),
        "evidence": normalize_evidence(record, source),
        "payload": {"source_kind": kind},
    }
    outcome = normalized_outcome(record, kind)
    if outcome:
        result["outcome"] = outcome
    for key in sorted(PAYLOAD_FIELDS):
        value = record.get(key)
        if value not in (None, "", [], {}):
            result["payload"][key] = value
    return result


def load_source_records(base: Path) -> Iterable[tuple[dict[str, Any], str, float]]:
    for name in ROTATED_LOGS:
        path = base / name
        if not path.exists():
            continue
        if path.is_symlink():
            raise ValueError(f"refusing symlinked source log: {path}")
        fallback = path.stat().st_mtime
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    yield record, f"{name}:{line_number}", fallback


def export_events(base: Path) -> list[dict[str, Any]]:
    if base.exists() and base.is_symlink():
        raise ValueError(f"refusing symlinked data directory: {base}")
    return [normalize_record(record, source, fallback) for record, source, fallback in load_source_records(base)]


def write_jsonl(events: Iterable[dict[str, Any]], output: str) -> None:
    encoded = "".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in events)
    if output == "-":
        sys.stdout.write(encoded)
        return
    path = Path(output).expanduser()
    if path.exists() and path.is_symlink():
        raise ValueError(f"refusing symlinked output: {path}")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(encoded)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="legacy ESRA runtime data directory")
    parser.add_argument("--output", default="-", help="JSONL path, or - for stdout")
    args = parser.parse_args(argv)
    try:
        write_jsonl(export_events(resolve_data_dir(args.data_dir)), args.output)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
