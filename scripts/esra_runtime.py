#!/usr/bin/env python3
"""Local, dependency-free ESRA runtime for Codex.

The runtime stores concise structured evidence, never full prompts, transcripts,
or hidden reasoning. It does not modify skills or promote experiments by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")
DECISIONS = {"adopt", "revise", "reject", "more-evidence"}
OUTCOMES = {"success", "partial", "failure", "blocked", "inconclusive"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def data_dir(override: str | None = None) -> Path:
    raw = override or os.environ.get("ESRA_DATA_DIR") or os.environ.get("PLUGIN_DATA")
    path = Path(raw).expanduser() if raw else Path.home() / ".codex" / "esra"
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing symlinked data directory: {path}")
    try:
        path.chmod(0o700)
    except OSError:
        pass
    return path


def safe_id(value: str, label: str = "identifier") -> str:
    if not SAFE_ID.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"unsafe {label}: {value!r}")
    return value


def digest(value: Any) -> str | None:
    if not value:
        return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def atomic_json(path: Path, payload: Any) -> None:
    if path.parent.exists() and path.parent.is_symlink():
        raise ValueError(f"refusing symlinked directory: {path.parent}")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise ValueError(f"refusing symlinked file: {path}")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    if path.is_symlink():
        raise ValueError(f"refusing symlinked file: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def append_event(base: Path, kind: str, **fields: Any) -> dict[str, Any]:
    event = {"id": uuid.uuid4().hex, "timestamp": utc_now(), "kind": kind}
    event.update({key: value for key, value in fields.items() if value not in (None, "")})
    encoded = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path = base / "events.jsonl"
    if path.exists() and path.is_symlink():
        raise ValueError(f"refusing symlinked file: {path}")
    max_bytes = int(os.environ.get("ESRA_MAX_LOG_BYTES", 5 * 1024 * 1024))
    if path.exists() and path.stat().st_size >= max_bytes:
        rotated = base / "events.1.jsonl"
        if rotated.exists() and rotated.is_symlink():
            raise ValueError(f"refusing symlinked file: {rotated}")
        os.replace(path, rotated)
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, encoded)
    finally:
        os.close(descriptor)
    return event


def load_events(base: Path, limit: int | None = None) -> list[dict[str, Any]]:
    path = base / "events.jsonl"
    if not path.exists():
        return []
    if path.is_symlink():
        raise ValueError(f"refusing symlinked file: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def record_hook(payload: dict[str, Any], base: Path) -> dict[str, Any]:
    """Record lifecycle counts without prompt, transcript, or raw identifiers."""
    event_name = str(payload.get("hook_event_name", "Unknown"))
    cwd = Path(str(payload.get("cwd", ""))).name or None
    return append_event(
        base,
        "lifecycle",
        event=event_name,
        session=digest(payload.get("session_id")),
        turn=digest(payload.get("turn_id")),
        workspace=cwd,
    )


def trigger_score(args: argparse.Namespace) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = max(0, min(args.complexity, 10))
    if args.complexity >= 7:
        reasons.append("high complexity")
    if args.major_change:
        score += 3
        reasons.append("major change")
    if args.new_skill:
        score += 3
        reasons.append("new or changed skill")
    if args.failures:
        score += min(args.failures * 2, 6)
        reasons.append(f"{args.failures} repeated failure(s)")
    if args.confidence < 0.5:
        score += 2
        reasons.append("low confidence")
    if args.explicit:
        score = 100
        reasons.append("explicit request")
    return score, reasons


def command_trigger(args: argparse.Namespace, base: Path) -> int:
    if args.failures == 0:
        recent_cycles = [event for event in load_events(base, 25) if event.get("kind") == "cycle"][-10:]
        args.failures = sum(event.get("outcome") in {"failure", "partial"} for event in recent_cycles)
    score, reasons = trigger_score(args)
    recent = [event for event in load_events(base) if event.get("kind") == "trigger"]
    today = utc_now()[:10]
    same_day = sum(str(item.get("timestamp", "")).startswith(today) and item.get("recommended") for item in recent)
    same_session = any(item.get("session") == args.session and item.get("recommended") for item in recent) if args.session else False
    recommended = score >= args.threshold
    limited = not args.force and (same_day >= args.daily_limit or same_session)
    if limited:
        recommended = False
        reasons.append("rate limit reached")
    result = append_event(
        base,
        "trigger",
        score=score,
        threshold=args.threshold,
        recommended=recommended,
        reasons=reasons,
        session=args.session,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_record(args: argparse.Namespace, base: Path) -> int:
    evidence = [item.strip() for item in args.evidence if item.strip()]
    result = append_event(
        base,
        "cycle",
        task=args.task,
        outcome=args.outcome,
        evidence=evidence,
        change=args.change,
        verification=args.verification,
        uncertainty=args.uncertainty,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def parse_metrics(items: Iterable[str]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for item in items:
        name, separator, value = item.partition("=")
        if not separator or not SAFE_ID.fullmatch(name):
            raise ValueError(f"metric must be NAME=NUMBER: {item!r}")
        metrics[name] = float(value)
    if not metrics:
        raise ValueError("at least one metric is required")
    return metrics


def command_baseline(args: argparse.Namespace, base: Path) -> int:
    snapshot = {
        "id": uuid.uuid4().hex,
        "timestamp": utc_now(),
        "name": safe_id(args.name, "baseline name"),
        "metrics": parse_metrics(args.metric),
        "notes": args.notes,
    }
    target = base / "baselines" / f"{snapshot['name']}.json"
    previous = read_json(target, {})
    history = list(previous.get("history", [])) if isinstance(previous, dict) else []
    if previous and "timestamp" in previous:
        history.append({key: previous.get(key) for key in ("id", "timestamp", "metrics", "notes")})
    snapshot["history"] = history[-99:]
    atomic_json(target, snapshot)
    append_event(base, "baseline", name=snapshot["name"], metrics=snapshot["metrics"])
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


def experiment_path(base: Path, experiment_id: str) -> Path:
    return base / "experiments" / f"{safe_id(experiment_id, 'experiment id')}.json"


def command_experiment_create(args: argparse.Namespace, base: Path) -> int:
    path = experiment_path(base, args.id)
    if path.exists():
        raise ValueError(f"experiment already exists: {args.id}")
    experiment = {
        "id": args.id,
        "created_at": utc_now(),
        "hypothesis": args.hypothesis,
        "baseline_command": shlex.split(args.baseline_command),
        "candidate_command": shlex.split(args.candidate_command),
        "guardrail": args.guardrail,
        "alignment_score": args.alignment_score,
        "minimum_alignment": args.minimum_alignment,
        "status": "draft",
        "runs": [],
        "decision": None,
    }
    if not experiment["baseline_command"] or not experiment["candidate_command"]:
        raise ValueError("baseline and candidate commands cannot be empty")
    if not 0 <= args.alignment_score <= 1 or not 0 <= args.minimum_alignment <= 1:
        raise ValueError("alignment scores must be between 0 and 1")
    atomic_json(path, experiment)
    append_event(base, "experiment-created", experiment=args.id)
    print(json.dumps(experiment, indent=2, sort_keys=True))
    return 0


def run_once(command: list[str], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
        return {
            "duration_seconds": round(time.monotonic() - started, 6),
            "exit_code": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout_tail": completed.stdout[-1000:],
            "stderr_tail": completed.stderr[-1000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "duration_seconds": round(time.monotonic() - started, 6),
            "exit_code": None,
            "ok": False,
            "timed_out": True,
            "stdout_tail": (exc.stdout or "")[-1000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-1000:] if isinstance(exc.stderr, str) else "",
        }


def trial_order(mode: str) -> list[str]:
    return {
        "canary": ["baseline", "candidate"],
        "staged": ["baseline", "candidate", "candidate", "candidate"],
        "ab": ["baseline", "candidate"] * 3,
        "stress": ["baseline"] * 3 + ["candidate"] * 10,
    }[mode]


def summarize_runs(runs: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for variant in ("baseline", "candidate"):
        relevant = [run for run in runs if run["variant"] == variant]
        durations = [float(run["duration_seconds"]) for run in relevant]
        summary[variant] = {
            "runs": len(relevant),
            "success_rate": round(sum(bool(run["ok"]) for run in relevant) / len(relevant), 3) if relevant else 0,
            "mean_seconds": round(sum(durations) / len(durations), 6) if durations else None,
        }
    baseline = summary["baseline"]
    candidate = summary["candidate"]
    if candidate["success_rate"] < baseline["success_rate"]:
        recommendation = "reject"
    elif mode == "canary":
        recommendation = "more-evidence"
    elif candidate["success_rate"] > baseline["success_rate"]:
        recommendation = "adopt"
    elif candidate["mean_seconds"] is not None and baseline["mean_seconds"] is not None and candidate["mean_seconds"] < baseline["mean_seconds"]:
        recommendation = "adopt"
    else:
        recommendation = "more-evidence"
    summary["recommendation"] = recommendation
    return summary


def command_experiment_run(args: argparse.Namespace, base: Path) -> int:
    path = experiment_path(base, args.id)
    experiment = read_json(path, None)
    if not experiment:
        raise ValueError(f"unknown experiment: {args.id}")
    if experiment.get("alignment_score", 1) < experiment.get("minimum_alignment", 0.6):
        experiment["status"] = "blocked"
        atomic_json(path, experiment)
        append_event(base, "experiment-blocked", experiment=args.id, reason="value alignment gate")
        print("Experiment blocked by its value-alignment gate.", file=sys.stderr)
        return 3
    if experiment.get("decision") == "adopt" and not args.rerun:
        raise ValueError("experiment was adopted; pass --rerun to collect another bounded sample")
    results: list[dict[str, Any]] = []
    for index, variant in enumerate(trial_order(args.mode), start=1):
        command = experiment[f"{variant}_command"]
        outcome = run_once(command, args.timeout)
        outcome.update({"index": index, "variant": variant, "timestamp": utc_now()})
        results.append(outcome)
        if variant == "candidate" and not outcome["ok"] and args.mode in {"canary", "staged"}:
            break
    run = {"id": uuid.uuid4().hex, "mode": args.mode, "timestamp": utc_now(), "results": results}
    run["summary"] = summarize_runs(results, args.mode)
    experiment.setdefault("runs", []).append(run)
    experiment["status"] = "evaluated"
    atomic_json(path, experiment)
    append_event(base, "experiment-run", experiment=args.id, mode=args.mode, recommendation=run["summary"]["recommendation"])
    print(json.dumps(run, indent=2, sort_keys=True))
    return 0 if all(item["ok"] for item in results) else 2


def command_experiment_decide(args: argparse.Namespace, base: Path) -> int:
    path = experiment_path(base, args.id)
    experiment = read_json(path, None)
    if not experiment:
        raise ValueError(f"unknown experiment: {args.id}")
    if not experiment.get("runs"):
        raise ValueError("run the experiment before recording a decision")
    experiment["decision"] = args.decision
    experiment["decision_notes"] = args.notes
    experiment["decided_at"] = utc_now()
    experiment["status"] = "closed" if args.decision != "revise" else "revision-needed"
    atomic_json(path, experiment)
    append_event(base, "experiment-decision", experiment=args.id, decision=args.decision)
    print(json.dumps({"id": args.id, "decision": args.decision, "status": experiment["status"]}, indent=2))
    return 0


def command_experiment_list(_args: argparse.Namespace, base: Path) -> int:
    directory = base / "experiments"
    rows = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        item = read_json(path, {})
        rows.append({"id": item.get("id"), "status": item.get("status"), "decision": item.get("decision"), "runs": len(item.get("runs", []))})
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


def command_experiment_report(args: argparse.Namespace, base: Path) -> int:
    experiment = read_json(experiment_path(base, args.id), None)
    if not experiment:
        raise ValueError(f"unknown experiment: {args.id}")
    report_dir = base / "reports"
    if report_dir.exists() and report_dir.is_symlink():
        raise ValueError(f"refusing symlinked directory: {report_dir}")
    report_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = report_dir / f"{safe_id(args.id, 'experiment id')}.md"
    lines = [
        f"# Experiment: {experiment['id']}",
        "",
        f"- Status: `{experiment.get('status')}`",
        f"- Decision: `{experiment.get('decision') or 'not recorded'}`",
        f"- Alignment: `{experiment.get('alignment_score', 1)}` (minimum `{experiment.get('minimum_alignment', 0.6)}`)",
        "",
        "## Hypothesis",
        "",
        str(experiment.get("hypothesis", "")),
        "",
        "## Guardrail",
        "",
        str(experiment.get("guardrail", "")),
        "",
        "## Runs",
        "",
    ]
    if not experiment.get("runs"):
        lines.append("No runs recorded.")
    for run in experiment.get("runs", []):
        summary = run.get("summary", {})
        lines.extend(
            [
                f"### {run.get('timestamp')} - {run.get('mode')}",
                "",
                f"- Baseline: `{summary.get('baseline')}`",
                f"- Candidate: `{summary.get('candidate')}`",
                f"- Recommendation: `{summary.get('recommendation')}`",
                "",
            ]
        )
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    target.chmod(0o600)
    append_event(base, "experiment-report", experiment=args.id, report=str(target))
    print(target)
    return 0


def validate_skill_tree(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"missing skill directory: {root}"]
    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlink not allowed: {path}")
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{directory.name}: missing SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            errors.append(f"{directory.name}: invalid frontmatter delimiters")
            continue
        header = text[4:].split("\n---\n", 1)[0]
        names = [line.split(":", 1)[1].strip() for line in header.splitlines() if line.startswith("name:")]
        descriptions = [line.split(":", 1)[1].strip() for line in header.splitlines() if line.startswith("description:")]
        if names != [directory.name]:
            errors.append(f"{directory.name}: name must match directory")
        if len(descriptions) != 1 or not descriptions[0]:
            errors.append(f"{directory.name}: one description is required")
        if len(text) > 30_000:
            errors.append(f"{directory.name}: SKILL.md is too large for selective loading")
    return errors


def command_validate(args: argparse.Namespace, _base: Path) -> int:
    root = Path(args.path).resolve()
    errors = validate_skill_tree(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Validated skill tree: {root}")
    return 0


def branch_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:48]
    return f"esra/{slug or 'review'}"


def command_oversight(args: argparse.Namespace, base: Path) -> int:
    review_id = safe_id(args.id, "review id")
    report = base / "reviews" / f"{review_id}.md"
    if report.parent.exists() and report.parent.is_symlink():
        raise ValueError(f"refusing symlinked directory: {report.parent}")
    report.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if report.exists() and report.is_symlink():
        raise ValueError(f"refusing symlinked report: {report}")
    body = (
        f"# {args.title}\n\n"
        f"- Review ID: `{review_id}`\n"
        f"- Suggested branch: `{branch_slug(args.title)}`\n"
        f"- Created: {utc_now()}\n\n"
        f"## Proposed change\n\n{args.summary}\n\n"
        f"## Evidence\n\n{args.evidence}\n\n"
        f"## Verification and rollback\n\n{args.verification}\n\n"
        "No change is approved or promoted by this report.\n"
    )
    report.write_text(body, encoding="utf-8")
    report.chmod(0o600)
    append_event(base, "oversight", review=review_id, report=str(report))
    print(report)
    return 0


def command_dashboard(args: argparse.Namespace, base: Path) -> int:
    events = load_events(base)
    kinds = Counter(str(event.get("kind", "unknown")) for event in events)
    outcomes = Counter(str(event.get("outcome")) for event in events if event.get("kind") == "cycle")
    payload = {
        "data_dir": str(base),
        "events": len(events),
        "event_types": dict(sorted(kinds.items())),
        "cycle_outcomes": dict(sorted(outcomes.items())),
        "last_event": events[-1].get("timestamp") if events else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ESRA events: {payload['events']}")
        print(f"Types: {payload['event_types']}")
        print(f"Cycle outcomes: {payload['cycle_outcomes']}")
        print(f"Last event: {payload['last_event'] or 'none'}")
    return 0


def command_audit(args: argparse.Namespace, base: Path) -> int:
    cycles = [event for event in load_events(base) if event.get("kind") == "cycle"][-args.limit :]
    outcomes = Counter(str(item.get("outcome")) for item in cycles)
    missing_verification = sum(not item.get("verification") for item in cycles)
    repeated_changes = Counter(str(item.get("change")) for item in cycles if item.get("change"))
    findings = []
    if not cycles:
        findings.append("No recorded cycles; cadence and recurrence are unknown.")
    if outcomes.get("failure", 0) + outcomes.get("partial", 0) >= 2:
        findings.append("Multiple non-success outcomes need a shared-cause review.")
    if missing_verification:
        findings.append(f"{missing_verification} cycle(s) lack verification evidence.")
    repeated = [change for change, count in repeated_changes.items() if count > 1]
    if repeated:
        findings.append("Repeated proposed changes: " + "; ".join(repeated[:3]))
    if cycles and not findings:
        findings.append("No recurring issue is supported by the available cycle records.")
    print(json.dumps({"cycles_reviewed": len(cycles), "outcomes": dict(outcomes), "findings": findings}, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local ESRA evidence and experiment runtime")
    parser.add_argument("--data-dir", help="override ESRA_DATA_DIR/PLUGIN_DATA")
    sub = parser.add_subparsers(dest="command", required=True)

    trigger = sub.add_parser("trigger", help="recommend (but never run) one bounded ESRA cycle")
    trigger.add_argument("--complexity", type=int, default=3)
    trigger.add_argument("--failures", type=int, default=0)
    trigger.add_argument("--confidence", type=float, default=0.8)
    trigger.add_argument("--major-change", action="store_true")
    trigger.add_argument("--new-skill", action="store_true")
    trigger.add_argument("--explicit", action="store_true")
    trigger.add_argument("--force", action="store_true")
    trigger.add_argument("--session")
    trigger.add_argument("--threshold", type=int, default=7)
    trigger.add_argument("--daily-limit", type=int, default=3)
    trigger.set_defaults(handler=command_trigger)

    record = sub.add_parser("record", help="store a concise evidence-backed cycle result")
    record.add_argument("--task", required=True)
    record.add_argument("--outcome", choices=sorted(OUTCOMES), required=True)
    record.add_argument("--evidence", action="append", default=[])
    record.add_argument("--change")
    record.add_argument("--verification")
    record.add_argument("--uncertainty")
    record.set_defaults(handler=command_record)

    baseline = sub.add_parser("baseline", help="store named numeric baseline metrics")
    baseline.add_argument("--name", required=True)
    baseline.add_argument("--metric", action="append", required=True)
    baseline.add_argument("--notes")
    baseline.set_defaults(handler=command_baseline)

    experiment = sub.add_parser("experiment", help="manage bounded command comparisons")
    experiment_sub = experiment.add_subparsers(dest="experiment_command", required=True)
    create = experiment_sub.add_parser("create")
    create.add_argument("id")
    create.add_argument("--hypothesis", required=True)
    create.add_argument("--baseline-command", required=True)
    create.add_argument("--candidate-command", required=True)
    create.add_argument("--guardrail", required=True)
    create.add_argument("--alignment-score", type=float, default=1.0)
    create.add_argument("--minimum-alignment", type=float, default=0.6)
    create.set_defaults(handler=command_experiment_create)
    run = experiment_sub.add_parser("run")
    run.add_argument("id")
    run.add_argument("--mode", choices=("canary", "staged", "ab", "stress"), default="canary")
    run.add_argument("--timeout", type=float, default=60)
    run.add_argument("--rerun", action="store_true")
    run.set_defaults(handler=command_experiment_run)
    decide = experiment_sub.add_parser("decide")
    decide.add_argument("id")
    decide.add_argument("--decision", choices=sorted(DECISIONS), required=True)
    decide.add_argument("--notes", required=True)
    decide.set_defaults(handler=command_experiment_decide)
    listing = experiment_sub.add_parser("list")
    listing.set_defaults(handler=command_experiment_list)
    report = experiment_sub.add_parser("report")
    report.add_argument("id")
    report.set_defaults(handler=command_experiment_report)

    validate = sub.add_parser("validate", help="validate a skill tree")
    validate.add_argument("path", nargs="?", default=str(ROOT / "skills"))
    validate.set_defaults(handler=command_validate)

    oversight = sub.add_parser("oversight", help="write a human-review artifact without promotion")
    oversight.add_argument("--id", required=True)
    oversight.add_argument("--title", required=True)
    oversight.add_argument("--summary", required=True)
    oversight.add_argument("--evidence", required=True)
    oversight.add_argument("--verification", required=True)
    oversight.set_defaults(handler=command_oversight)

    dashboard = sub.add_parser("dashboard", help="summarize local ESRA records")
    dashboard.add_argument("--json", action="store_true")
    dashboard.set_defaults(handler=command_dashboard)

    audit = sub.add_parser("audit", help="inspect recent recorded cycles")
    audit.add_argument("--limit", type=int, default=10)
    audit.set_defaults(handler=command_audit)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        base = data_dir(args.data_dir)
        return int(args.handler(args, base))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
