#!/usr/bin/env python3
"""Guard: every engineering-series skill carries its source-marker name.

ADR 0007 Decision 3 makes the SKILL.md frontmatter ``name:`` field the
source marker of an engineering-series skill (directories ``engineering-*``,
``*-sessions``, ``*-watch``): the marker must exist and match the directory
name, because the routing-table registry keys rows by it. A series skill
that renders without its marker would be unregistrable and unroutable while
still visible on disk, so this test fails closed on a missing or mismatched
marker. The real enforcement is review; this guard only keeps the floor.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SERIES_PATTERNS = ("engineering-*/SKILL.md", "*-sessions/SKILL.md", "*-watch/SKILL.md")
NAME_LINE = re.compile(r"^name:\s*(?P<name>.+?)\s*$", re.MULTILINE)
EXPECTED_SERIES = (
    "engineering-init",
    "engineering-process",
    "engineering-research",
    "engineering-routing",
    "openhands-sessions",
    "openhands-watch",
)
CONTRACT = ROOT / "engineering-routing" / "references" / "routing-table.md"
CONTRACT_COLUMNS = "| skill | state | group | entry | uses |"
CONTRACT_STATES = ("registered", "enabled")
CONTRACT_GROUPS = ("office", "hardware", "research", "process")


def series_source_markers(root: Path) -> dict[str, str | None]:
    """Discover engineering-series skills and extract their source markers.

    Args:
        root: Repository root holding the series skill directories.

    Returns:
        Mapping from skill directory name to the declared frontmatter
        ``name:`` value, or ``None`` when SKILL.md is missing, has no
        frontmatter, or declares no name.
    """
    markers: dict[str, str | None] = {}
    for pattern in SERIES_PATTERNS:
        for skill_md in sorted(root.glob(pattern)):
            directory = skill_md.parent.name
            if directory in markers:
                continue
            markers[directory] = _frontmatter_name(skill_md)
    return markers


def _frontmatter_name(skill_md: Path) -> str | None:
    """Return the frontmatter ``name:`` value of a SKILL.md, or None."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    frontmatter = re.match(
        r"^---[ \t]*\n(?P<body>.*?)\n---[ \t]*$", text, re.DOTALL | re.MULTILINE
    )
    if frontmatter is None:
        return None
    match = NAME_LINE.search(frontmatter.group("body"))
    return match["name"] if match else None


def missing_source_markers(root: Path) -> list[str]:
    """Return engineering-series skills whose source marker is missing.

    Args:
        root: Repository root (or scratch tree) holding skill directories.

    Returns:
        Human-readable offender lines for every series directory whose
        SKILL.md lacks a frontmatter name or whose name mismatches the
        directory name.
    """
    offenders = []
    for directory, declared in series_source_markers(root).items():
        if declared != directory:
            offenders.append(f"{directory}: name={declared!r} != directory name")
    return offenders


class RepoSourceMarkerTests(unittest.TestCase):
    """The real repo must carry the marker on every series skill."""

    def test_repo_series_skills_all_marked(self) -> None:
        offenders = missing_source_markers(ROOT)
        self.assertEqual(offenders, [])

    def test_series_coverage_cannot_shrink(self) -> None:
        discovered = set(series_source_markers(ROOT))
        self.assertEqual(discovered, set(EXPECTED_SERIES))


class FabricatedSkillTests(unittest.TestCase):
    """The failing direction must be proven non-vacuously, off-repo."""

    def _write_skill(self, directory: Path, name: str | None) -> None:
        body = (
            "---\n"
            + (f"name: {name}\n" if name is not None else "")
            + "description: fabricated probe\n"
            + "---\n\n# probe\n"
        )
        (directory).mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(body, encoding="utf-8")

    def test_missing_mismatched_and_marked_are_distinguished(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_skill(root / "engineering-pcb", None)
            self._write_skill(root / "engineering-ppt", "wrong-name")
            self._write_skill(root / "engineering-probe", "engineering-probe")
            (root / "not-a-series").mkdir()
            offenders = missing_source_markers(root)
        self.assertEqual(len(offenders), 2)
        self.assertTrue(any(line.startswith("engineering-pcb:") for line in offenders))
        self.assertTrue(any(line.startswith("engineering-ppt:") for line in offenders))
        self.assertNotIn("engineering-probe", " ".join(offenders))


class RoutingTableContractTests(unittest.TestCase):
    """The registry contract file must exist with its format anchors."""

    def test_routing_table_contract_anchors(self) -> None:
        self.assertTrue(CONTRACT.is_file(), CONTRACT)
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn(CONTRACT_COLUMNS, text)
        for state in CONTRACT_STATES:
            self.assertIn(state, text)
        for group in CONTRACT_GROUPS:
            self.assertIn(group, text)


if __name__ == "__main__":
    unittest.main()
