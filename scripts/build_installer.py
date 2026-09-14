#!/usr/bin/env python3
"""Build the self-contained local marketplace distributed in GitHub Releases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ARCHIVE_ROOT = "esra-installer"
PLUGIN_NAME = "chatgpt-esra"
MARKETPLACE = {
    "name": "esra",
    "interface": {"displayName": "ESRA"},
    "plugins": [
        {
            "name": PLUGIN_NAME,
            "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
            "policy": {
                "installation": "AVAILABLE",
                "authentication": "ON_INSTALL",
            },
            "category": "Developer Tools",
        }
    ],
}

PLUGIN_FILES = (
    ".codex-plugin/plugin.json",
    "INSTALL.md",
    "LICENSE",
    "NOTICE",
    "README.md",
    "esra-conformance.json",
    "plugin.json",
    "scripts/esra_export.py",
    "scripts/esra_hook.py",
    "scripts/esra_runtime.py",
    "scripts/validate_skills.py",
)
PLUGIN_DIRECTORIES = ("assets", "docs", "hooks", "skills")


def archive_info(name: str) -> ZipInfo:
    info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def add_bytes(archive: ZipFile, name: str, data: bytes) -> None:
    archive.writestr(archive_info(name), data)


def included_plugin_files(repo_root: Path) -> list[Path]:
    files = [repo_root / relative for relative in PLUGIN_FILES]
    for directory in PLUGIN_DIRECTORIES:
        files.extend(
            path
            for path in (repo_root / directory).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        )
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing installer input: {missing[0]}")
    return sorted(set(files))


def build(output: Path) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    output.parent.mkdir(parents=True, exist_ok=True)
    marketplace_path = f"{ARCHIVE_ROOT}/.agents/plugins/marketplace.json"
    install_path = f"{ARCHIVE_ROOT}/INSTALL.md"
    plugin_prefix = f"{ARCHIVE_ROOT}/plugins/{PLUGIN_NAME}"

    with ZipFile(output, "w") as archive:
        add_bytes(
            archive,
            marketplace_path,
            (json.dumps(MARKETPLACE, indent=2) + "\n").encode(),
        )
        add_bytes(archive, install_path, (repo_root / "INSTALL.md").read_bytes())
        for source in included_plugin_files(repo_root):
            relative = source.relative_to(repo_root).as_posix()
            add_bytes(archive, f"{plugin_prefix}/{relative}", source.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default="dist/esra-installer.zip")
    args = parser.parse_args()
    build(Path(args.output).resolve())


if __name__ == "__main__":
    main()
