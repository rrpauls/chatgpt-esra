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
        portable = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        compatibility = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            portable["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertNotIn("skills", portable)
        self.assertEqual(
            portable["extensions"]["com.openai"]["hooks"], "./hooks/hooks.json"
        )
        self.assertIn("interface", portable["extensions"]["com.openai"])
        self.assertEqual(compatibility["skills"], "./skills/")
        self.assertIn("interface", compatibility)
        for manifest in (portable, compatibility):
            self.assertEqual(manifest["name"], "chatgpt-esra")
            self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")

        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        entry = marketplace["plugins"][0]
        self.assertEqual(marketplace["name"], "esra")
        self.assertEqual(entry["name"], "chatgpt-esra")
        self.assertEqual(entry["source"]["source"], "url")
        self.assertEqual(entry["source"]["ref"], "v0.4.1")
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
