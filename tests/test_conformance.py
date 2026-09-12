import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "esra-conformance.json"
ALLOWED_STATUSES = {
    "implemented",
    "verified",
    "simulated",
    "planned",
    "not-applicable",
}


class ConformanceDeclarationTests(unittest.TestCase):
    def test_manifest_has_versioned_evidence_backed_capabilities(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertRegex(
            data["implementation_version"],
            r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$",
        )
        self.assertEqual(data["protocol_version"], "1.2")
        self.assertTrue(data["implementation"])
        self.assertTrue(data["runtime"])
        self.assertTrue(data["capabilities"])

        for name, capability in data["capabilities"].items():
            with self.subTest(capability=name):
                self.assertIn(capability["status"], ALLOWED_STATUSES)
                self.assertTrue(capability["evidence"])
                for reference in capability["evidence"]:
                    evidence_path = ROOT / reference.split("#", 1)[0]
                    self.assertTrue(
                        evidence_path.exists(),
                        f"missing evidence path: {reference}",
                    )


if __name__ == "__main__":
    unittest.main()
