import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.build_installer import ARCHIVE_ROOT, PLUGIN_NAME, build


class InstallerTests(unittest.TestCase):
    def test_archive_is_a_self_contained_marketplace(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "esra-installer.zip"
            build(output)

            with ZipFile(output) as archive:
                names = set(archive.namelist())
                marketplace_name = f"{ARCHIVE_ROOT}/.agents/plugins/marketplace.json"
                manifest_name = (
                    f"{ARCHIVE_ROOT}/plugins/{PLUGIN_NAME}/.codex-plugin/plugin.json"
                )
                self.assertIn(f"{ARCHIVE_ROOT}/INSTALL.md", names)
                self.assertIn(marketplace_name, names)
                self.assertIn(manifest_name, names)
                self.assertFalse(any("__pycache__" in name for name in names))
                self.assertFalse(any(name.endswith("build_installer.py") for name in names))

                marketplace = json.loads(archive.read(marketplace_name))
                entry = marketplace["plugins"][0]
                self.assertEqual("esra", marketplace["name"])
                self.assertEqual(PLUGIN_NAME, entry["name"])
                self.assertEqual(
                    f"./plugins/{PLUGIN_NAME}", entry["source"]["path"]
                )


if __name__ == "__main__":
    unittest.main()
