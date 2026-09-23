#!/usr/bin/env python3
"""Tests for the skill-maker registrar checklist.

Real-repo tests pin the privilege anchors in ``skill-maker/SKILL.md``, the
ADR 0006 Decision 3 coverage in ``references/privileges.md``, and the
``registered`` state of the real ``skill-maker`` routing-table row. The
``validate_registration`` directions run off-repo in fabricated trees so a
failing assertion can only come from the validator, never from repo state.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from registrar_check import validate_registration

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = "skill-maker"
SKILL_MD = REPO_ROOT / "skill-maker" / "SKILL.md"
PRIVILEGES_MD = REPO_ROOT / "skill-maker" / "references" / "privileges.md"
TABLE_MD = REPO_ROOT / "engineering-routing" / "references" / "routing-table.md"

TABLE_HEADER = [
    "| skill | state | group | entry | uses |",
    "| --- | --- | --- | --- | --- |",
]
EXISTING_ROW = "| engineering-routing | enabled | writer | engineering-routing | — |"

PRIVILEGE_ANCHORS = (
    "Exclusive engineering-series modifier",
    "**Registrar**",
    "No ownership of product craft content",
)
PRIVILEGES_SECTION_ANCHORS = (
    "## 1. Exclusive engineering-series modifier",
    "## 2. Registrar",
    "## 3. No ownership of product craft content",
)
REGISTRAR_PROCEDURE_ANCHORS = (
    "Skill files land in the repo",
    "Spec contains/uses entry added",
    "Exactly one routing-table row appended",
    "Never engine code",
    "Registration never dispatches anything",
)


def make_row(
    name: str, state: str = "registered", group: str = "—", uses: str = "—"
) -> str:
    """Build a routing-table row for a fabricated skill.

    Args:
        name: Skill name filling the skill and entry cells.
        state: Value for the state cell.
        group: Value for the group cell.
        uses: Value for the uses cell.

    Returns:
        One 5-column Markdown table row.
    """
    return f"| {name} | {state} | {group} | {name} | {uses} |"


class RegistrarAnchorsTest(unittest.TestCase):
    """Real-repo anchors: privilege split and registrar procedure."""

    def test_skill_md_carries_three_privilege_anchors(self) -> None:
        """SKILL.md states all three separated privileges."""
        text = SKILL_MD.read_text(encoding="utf-8")
        for anchor in PRIVILEGE_ANCHORS:
            self.assertIn(anchor, text)

    def test_skill_md_carries_registrar_procedure_anchors(self) -> None:
        """SKILL.md lists the registration procedure step-for-step."""
        text = SKILL_MD.read_text(encoding="utf-8")
        position = -1
        for anchor in REGISTRAR_PROCEDURE_ANCHORS:
            position = text.find(anchor, position + 1)
            self.assertGreaterEqual(position, 0, f"missing or out of order: {anchor}")

    def test_privileges_reference_covers_adr_decision_3(self) -> None:
        """references/privileges.md exists and cites ADR 0006 Decision 3."""
        text = PRIVILEGES_MD.read_text(encoding="utf-8")
        self.assertIn("ADR 0006", text)
        self.assertIn("Decision 3", text)
        for anchor in PRIVILEGES_SECTION_ANCHORS:
            self.assertIn(anchor, text)


class RealRoutingTableRowTest(unittest.TestCase):
    """The real routing table read directly, no cross-skill imports."""

    def test_skill_maker_row_is_registered_with_empty_group_and_uses(self) -> None:
        """The skill-maker row is registered and not enablement-claimed."""
        rows = [
            line
            for line in TABLE_MD.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("|") and line.split("|")[1].strip() == SKILL
        ]
        self.assertEqual(len(rows), 1, f"expected one {SKILL} row, got {rows}")
        cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
        self.assertEqual(len(cells), 5)
        skill, state, group, entry, uses = cells
        self.assertEqual(skill, "skill-maker")
        self.assertEqual(state, "registered")
        # The real table renders empty cells as an em-dash.
        self.assertIn(group, ("", "—"))
        self.assertEqual(entry, "skill-maker")
        self.assertIn(uses, ("", "—"))


class ValidateRegistrationTest(unittest.TestCase):
    """Fabricated-tree directions for validate_registration."""

    def setUp(self) -> None:
        """Create a fabricated repo tree with a skill and a routing table."""
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.table_rel = "engineering-routing/references/routing-table.md"
        self.table = self.root / self.table_rel
        self.table.parent.mkdir(parents=True)
        self.table.write_text(
            "\n".join([*TABLE_HEADER, EXISTING_ROW, ""]), encoding="utf-8"
        )

    def add_skill(self, name: str, frontmatter_name: str | None = None) -> None:
        """Write ``<name>/SKILL.md`` into the fabricated tree.

        Args:
            name: Directory name of the fabricated skill.
            frontmatter_name: Declared frontmatter name; defaults to ``name``.
        """
        declared = name if frontmatter_name is None else frontmatter_name
        skill_dir = self.root / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {declared}\ndescription: demo\n---\n\n# {declared}\n",
            encoding="utf-8",
        )

    def validate(self, row: str, changed: list[str]) -> list[str]:
        """Run the validator against the fabricated tree.

        Args:
            row: Proposed routing-table row.
            changed: Changed-path list handed to the validator.

        Returns:
            Offender strings from ``validate_registration``.
        """
        return validate_registration(self.root, changed, self.table, row)

    def test_valid_registration_passes(self) -> None:
        """A complete registration returns no offenders."""
        self.add_skill("demo-craft")
        row = make_row("demo-craft")
        self.table.write_text(
            "\n".join([*TABLE_HEADER, EXISTING_ROW, row, ""]), encoding="utf-8"
        )
        offenders = self.validate(row, ["demo-craft/SKILL.md", self.table_rel])
        self.assertEqual(offenders, [])

    def test_missing_skill_md_fails(self) -> None:
        """A registration without the skill file on disk fails."""
        row = make_row("demo-craft")
        offenders = self.validate(row, [self.table_rel])
        self.assertTrue(any(o.startswith("files:") for o in offenders), offenders)

    def test_name_mismatch_fails(self) -> None:
        """A frontmatter name differing from the directory name fails."""
        self.add_skill("demo-craft", frontmatter_name="other-name")
        row = make_row("demo-craft")
        offenders = self.validate(row, ["demo-craft/SKILL.md", self.table_rel])
        self.assertTrue(any("name=" in o for o in offenders), offenders)

    def test_wrong_state_fails(self) -> None:
        """A row claiming ``enabled`` fails; enablement is a separate ticket."""
        self.add_skill("demo-craft")
        row = make_row("demo-craft", state="enabled")
        offenders = self.validate(row, ["demo-craft/SKILL.md", self.table_rel])
        self.assertTrue(any(o.startswith("state:") for o in offenders), offenders)

    def test_non_empty_group_fails(self) -> None:
        """A non-empty group cell fails on a registered row."""
        self.add_skill("demo-craft")
        row = make_row("demo-craft", group="writer")
        offenders = self.validate(row, ["demo-craft/SKILL.md", self.table_rel])
        self.assertTrue(any(o.startswith("group:") for o in offenders), offenders)

    def test_non_empty_uses_fails(self) -> None:
        """A sessions-style uses value fails on a registered row."""
        self.add_skill("demo-craft")
        row = make_row("demo-craft", uses="-> engineering-sessions")
        offenders = self.validate(row, ["demo-craft/SKILL.md", self.table_rel])
        self.assertTrue(any(o.startswith("uses:") for o in offenders), offenders)

    def test_engine_code_path_fails(self) -> None:
        """Engineering-series engine code in changed_paths fails closed."""
        self.add_skill("demo-craft")
        row = make_row("demo-craft")
        changed = [
            "demo-craft/SKILL.md",
            self.table_rel,
            "engineering-routing/scripts/routing_table.py",
            "engineering-init/scripts/verify.py",
        ]
        offenders = self.validate(row, changed)
        engine = [o for o in offenders if o.startswith("engine code:")]
        self.assertEqual(len(engine), 2, offenders)
        self.assertTrue(any("routing_table.py" in o for o in engine))
        self.assertTrue(any("verify.py" in o for o in engine))

    def test_table_file_itself_is_not_engine_code(self) -> None:
        """The routing table counts as data, never engine code."""
        self.add_skill("demo-craft")
        row = make_row("demo-craft")
        offenders = self.validate(row, ["demo-craft/SKILL.md", self.table_rel])
        self.assertEqual(
            [o for o in offenders if o.startswith("engine code:")], [], offenders
        )

    def test_row_not_appended_fails(self) -> None:
        """A row absent from the table file fails."""
        self.add_skill("demo-craft")
        row = make_row("demo-craft")
        offenders = self.validate(row, ["demo-craft/SKILL.md", self.table_rel])
        self.assertEqual([o for o in offenders if o.startswith("table:")],
                         [f"table: row not appended in {self.table}"], offenders)

    def test_changed_paths_missing_table_fails(self) -> None:
        """A patch that does not touch the table file cannot append a row."""
        self.add_skill("demo-craft")
        row = make_row("demo-craft")
        offenders = self.validate(row, ["demo-craft/SKILL.md"])
        self.assertTrue(any("changed_paths:" in o for o in offenders), offenders)

    def test_malformed_row_fails(self) -> None:
        """Non-row text and wrong column counts fail closed."""
        self.add_skill("demo-craft")
        for row in ("append demo-craft", "| demo-craft | registered | — |"):
            with self.subTest(row=row):
                offenders = self.validate(row, ["demo-craft/SKILL.md", self.table_rel])
                self.assertTrue(any(o.startswith("row:") for o in offenders), offenders)


if __name__ == "__main__":
    unittest.main()
