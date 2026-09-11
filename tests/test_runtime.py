from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "esra_runtime", ROOT / "scripts" / "esra_runtime.py"
)
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = RUNTIME.data_dir(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_hook_discards_sensitive_content_and_hashes_ids(self) -> None:
        RUNTIME.record_hook(
            {
                "hook_event_name": "Stop",
                "session_id": "raw-session-secret",
                "turn_id": "raw-turn-secret",
                "cwd": "/private/work/example",
                "prompt": "do not retain this prompt",
                "transcript_path": "/private/transcript.jsonl",
                "tool_input": {"token": "secret"},
            },
            self.base,
        )
        raw = (self.base / "events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("raw-session-secret", raw)
        self.assertNotIn("raw-turn-secret", raw)
        self.assertNotIn("do not retain", raw)
        self.assertNotIn("transcript", raw)
        event = RUNTIME.load_events(self.base)[0]
        self.assertEqual(event["event"], "Stop")
        self.assertEqual(event["workspace"], "example")
        self.assertEqual(len(event["session"]), 12)

    def test_trigger_scores_and_rate_limits_by_session(self) -> None:
        args = argparse.Namespace(
            complexity=8,
            failures=0,
            confidence=0.8,
            major_change=True,
            new_skill=False,
            explicit=False,
            force=False,
            session="session-one",
            threshold=7,
            daily_limit=3,
        )
        self.assertEqual(RUNTIME.command_trigger(args, self.base), 0)
        self.assertEqual(RUNTIME.command_trigger(args, self.base), 0)
        events = RUNTIME.load_events(self.base)
        self.assertTrue(events[0]["recommended"])
        self.assertFalse(events[1]["recommended"])
        self.assertIn("rate limit reached", events[1]["reasons"])

    def test_baseline_snapshot(self) -> None:
        args = argparse.Namespace(name="quality", metric=["pass_rate=1", "seconds=2.5"], notes="fixture")
        self.assertEqual(RUNTIME.command_baseline(args, self.base), 0)
        snapshot = json.loads((self.base / "baselines" / "quality.json").read_text())
        self.assertEqual(snapshot["metrics"], {"pass_rate": 1.0, "seconds": 2.5})
        self.assertEqual(snapshot["history"], [])
        args.metric = ["pass_rate=0.9"]
        RUNTIME.command_baseline(args, self.base)
        updated = json.loads((self.base / "baselines" / "quality.json").read_text())
        self.assertEqual(len(updated["history"]), 1)

    def test_canary_experiment_lifecycle(self) -> None:
        executable = shlex_quote(sys.executable)
        create = argparse.Namespace(
            id="canary-demo",
            hypothesis="candidate remains successful",
            baseline_command=f"{executable} -c 'print(1)'",
            candidate_command=f"{executable} -c 'print(2)'",
            guardrail="both exit zero",
            alignment_score=1.0,
            minimum_alignment=0.6,
        )
        self.assertEqual(RUNTIME.command_experiment_create(create, self.base), 0)
        run = argparse.Namespace(id="canary-demo", mode="canary", timeout=5, rerun=False)
        self.assertEqual(RUNTIME.command_experiment_run(run, self.base), 0)
        decide = argparse.Namespace(id="canary-demo", decision="more-evidence", notes="one sample")
        self.assertEqual(RUNTIME.command_experiment_decide(decide, self.base), 0)
        self.assertEqual(RUNTIME.command_experiment_report(argparse.Namespace(id="canary-demo"), self.base), 0)
        experiment = json.loads(RUNTIME.experiment_path(self.base, "canary-demo").read_text())
        self.assertEqual(len(experiment["runs"][0]["results"]), 2)
        self.assertEqual(experiment["runs"][0]["summary"]["recommendation"], "more-evidence")
        self.assertEqual(experiment["decision"], "more-evidence")

    def test_canary_stops_after_candidate_failure(self) -> None:
        executable = shlex_quote(sys.executable)
        create = argparse.Namespace(
            id="failure-demo",
            hypothesis="fixture",
            baseline_command=f"{executable} -c 'raise SystemExit(0)'",
            candidate_command=f"{executable} -c 'raise SystemExit(3)'",
            guardrail="stop on candidate failure",
            alignment_score=1.0,
            minimum_alignment=0.6,
        )
        RUNTIME.command_experiment_create(create, self.base)
        run = argparse.Namespace(id="failure-demo", mode="staged", timeout=5, rerun=False)
        self.assertEqual(RUNTIME.command_experiment_run(run, self.base), 2)
        experiment = json.loads(RUNTIME.experiment_path(self.base, "failure-demo").read_text())
        self.assertEqual(len(experiment["runs"][0]["results"]), 2)
        self.assertEqual(experiment["runs"][0]["summary"]["recommendation"], "reject")

    def test_experiment_value_alignment_gate_blocks_execution(self) -> None:
        executable = shlex_quote(sys.executable)
        create = argparse.Namespace(
            id="blocked-demo",
            hypothesis="fixture",
            baseline_command=f"{executable} -c 'print(1)'",
            candidate_command=f"{executable} -c 'print(2)'",
            guardrail="do not execute below threshold",
            alignment_score=0.2,
            minimum_alignment=0.6,
        )
        RUNTIME.command_experiment_create(create, self.base)
        run = argparse.Namespace(id="blocked-demo", mode="canary", timeout=5, rerun=False)
        self.assertEqual(RUNTIME.command_experiment_run(run, self.base), 3)
        experiment = json.loads(RUNTIME.experiment_path(self.base, "blocked-demo").read_text())
        self.assertEqual(experiment["status"], "blocked")
        self.assertEqual(experiment["runs"], [])

    def test_skill_tree_validation_and_safe_identifiers(self) -> None:
        self.assertEqual(RUNTIME.validate_skill_tree(ROOT / "skills"), [])
        for unsafe in ("../escape", "/absolute", "with space", ""):
            with self.assertRaises(ValueError):
                RUNTIME.safe_id(unsafe)

    def test_event_log_rotates_at_configured_limit(self) -> None:
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"ESRA_MAX_LOG_BYTES": "1"}):
            RUNTIME.append_event(self.base, "first")
            RUNTIME.append_event(self.base, "second")
        self.assertTrue((self.base / "events.1.jsonl").is_file())
        self.assertEqual(RUNTIME.load_events(self.base)[0]["kind"], "second")


def shlex_quote(value: str) -> str:
    """Quote an executable path for the runtime's shlex parser."""
    import shlex

    return shlex.quote(value)


if __name__ == "__main__":
    unittest.main()
