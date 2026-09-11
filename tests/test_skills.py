from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_skills", ROOT / "scripts" / "validate_skills.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class SkillValidationTests(unittest.TestCase):
    def test_repository_skills_are_valid(self) -> None:
        self.assertEqual(VALIDATOR.validate(), [])

    def test_every_skill_has_a_routine_bypass_or_narrow_trigger(self) -> None:
        for skill in sorted(VALIDATOR.EXPECTED):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8").lower()
            has_boundary = any(
                phrase in text
                for phrase in (
                    "skip routine",
                    "not required for ordinary",
                    "skip straightforward",
                    "skip ordinary",
                    "routine answers",
                    "recurring errors",
                )
            )
            self.assertTrue(has_boundary, skill)

    def test_orchestrator_blocks_recursive_reviews(self) -> None:
        text = (
            ROOT / "skills" / "esra-orchestrator" / "SKILL.md"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("never let an esra review", text)
        self.assertIn("one review per primary task", text)

    def test_plugin_manifests_and_skill_metadata_are_present(self) -> None:
        manifests = [ROOT / "plugin.json", ROOT / ".codex-plugin" / "plugin.json"]
        for manifest in manifests:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["name"], "chatgpt-esra")
            self.assertRegex(data["version"], r"^\d+\.\d+\.\d+$")
            self.assertEqual(data["skills"], "./skills/")
            self.assertIn("interface", data)
        for skill in VALIDATOR.EXPECTED:
            metadata = ROOT / "skills" / skill / "agents" / "openai.yaml"
            self.assertTrue(metadata.is_file(), skill)
            self.assertIn("display_name:", metadata.read_text(encoding="utf-8"))

    def test_hook_is_non_steering_and_uses_plugin_paths(self) -> None:
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data["hooks"]), {"UserPromptSubmit", "Stop", "SessionEnd"})
        raw = json.dumps(data)
        self.assertIn("$PLUGIN_ROOT/scripts/esra_hook.py", raw)
        self.assertNotIn("additionalContext", raw)
        self.assertNotIn("decision", raw.lower())


if __name__ == "__main__":
    unittest.main()
