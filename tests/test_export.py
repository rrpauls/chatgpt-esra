from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("esra_export", ROOT / "scripts" / "esra_export.py")
assert SPEC and SPEC.loader
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class ExportTests(unittest.TestCase):
    def test_exports_schema_shaped_events_and_redacts_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            records = [
                {
                    "id": "cycle-1",
                    "timestamp": "2026-09-12T18:00:00+00:00",
                    "kind": "cycle",
                    "task": "adapter",
                    "outcome": "success",
                    "evidence": ["tests passed"],
                    "verification": "schema validation",
                    "prompt": "private prompt",
                    "stdout": "secret output",
                    "session": "raw-session",
                },
                {
                    "timestamp": "2026-09-12T18:01:00+00:00",
                    "kind": "experiment-blocked",
                    "experiment": "exp-1",
                },
            ]
            (base / "events.jsonl").write_text(
                "".join(json.dumps(item) + "\n" for item in records), encoding="utf-8"
            )

            exported = EXPORT.export_events(base)
            self.assertEqual(len(exported), 2)
            self.assertEqual(exported[0]["implementation"], "chatgpt-esra")
            self.assertEqual(exported[0]["event_type"], "integration")
            self.assertEqual(exported[0]["outcome"], "success")
            self.assertEqual(exported[1]["outcome"], "not-run")
            raw = json.dumps(exported)
            self.assertNotIn("private prompt", raw)
            self.assertNotIn("secret output", raw)
            self.assertNotIn("raw-session", raw)

    def test_output_is_deterministic_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary) / "data"
            base.mkdir()
            (base / "events.jsonl").write_text(
                '{"timestamp":"2026-09-12T18:00:00Z","kind":"trigger","recommended":true}\n',
                encoding="utf-8",
            )
            first = EXPORT.export_events(base)
            second = EXPORT.export_events(base)
            self.assertEqual(first, second)
            output = Path(temporary) / "portable.jsonl"
            EXPORT.write_jsonl(first, str(output))
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(output.read_text()), first[0])


if __name__ == "__main__":
    unittest.main()
