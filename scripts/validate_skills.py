#!/usr/bin/env python3
"""Validate the compact ESRA skill set using only the Python standard library."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
EXPECTED = {
    "esra-orchestrator",
    "esra-decisions",
    "esra-experiments",
    "esra-reflection",
    "esra-crisis",
}
FORBIDDEN = (
    "~/.hermes",
    "$HERMES_HOME",
)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing opening frontmatter delimiter")
    try:
        raw, _body = text[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc

    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        match = re.fullmatch(r"([a-z][a-z0-9_-]*):\s*(.+)", line)
        if not match:
            raise ValueError(f"invalid frontmatter line: {line!r}")
        metadata[match.group(1)] = match.group(2).strip()
    return metadata


def validate(root: Path = SKILLS_DIR) -> list[str]:
    errors: list[str] = []
    found = {path.name for path in root.iterdir() if path.is_dir()} if root.exists() else set()

    if found != EXPECTED:
        errors.append(
            f"skill directories differ: missing={sorted(EXPECTED - found)}, "
            f"unexpected={sorted(found - EXPECTED)}"
        )

    seen_names: set[str] = set()
    for directory in sorted(found):
        skill_file = root / directory / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{directory}: missing SKILL.md")
            continue

        text = skill_file.read_text(encoding="utf-8")
        try:
            metadata = parse_frontmatter(text)
        except ValueError as exc:
            errors.append(f"{directory}: {exc}")
            continue

        name = metadata.get("name", "")
        description = metadata.get("description", "")
        if name != directory:
            errors.append(f"{directory}: frontmatter name is {name!r}")
        if name in seen_names:
            errors.append(f"{directory}: duplicate name {name!r}")
        seen_names.add(name)
        if not description:
            errors.append(f"{directory}: missing description")
        elif len(description) > 1024:
            errors.append(f"{directory}: description exceeds 1024 characters")

        for phrase in FORBIDDEN:
            if phrase.lower() in text.lower():
                errors.append(f"{directory}: contains forbidden host assumption {phrase!r}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Validated {len(EXPECTED)} ESRA skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
