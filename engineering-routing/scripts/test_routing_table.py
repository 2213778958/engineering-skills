#!/usr/bin/env python3
"""Tests: the routing table parses, fails closed, and answers route/skip.

The real repository table must parse into exactly the registered series
and answer routing decisions from it (ADR 0007: the table is data; this
module is its consumer). The fabricated-tree direction proves the failing
cases are non-vacuous, off-repo: malformed rows, duplicate names, and
unknown skills must fail closed instead of routing by guess.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import routing_table

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "engineering-routing" / "references" / "routing-table.md"

ENABLED = (
    "engineering-init",
    "engineering-process",
    "engineering-research",
    "engineering-sessions",
)
REGISTERED = (
    "engineering-routing",
    "openhands-sessions",
    "openhands-watch",
    "skill-maker",
)
HEADER = "| skill | state | group | entry | uses |"
SEPARATOR = "|---|---|---|---|---|"


def _row(skill: str, state: str, group: str, entry: str, uses: str) -> str:
    """Render one fabricated table row."""
    return f"| {skill} | {state} | {group} | {entry} | {uses} |"


def _table(*rows: str) -> str:
    """Render a fabricated table body from the header and given rows."""
    return "\n".join([HEADER, SEPARATOR, *rows])


def write_table(root: Path, body: str) -> Path:
    """Write a fabricated routing table into a scratch tree.

    Args:
        root: Scratch root receiving the fabricated skill tree.
        body: Full Markdown text of the fabricated table.

    Returns:
        Path of the written table file.
    """
    references = root / "engineering-routing" / "references"
    references.mkdir(parents=True)
    table = references / "routing-table.md"
    table.write_text(body, encoding="utf-8")
    return table


class RepoRoutingTableTests(unittest.TestCase):
    """The real repo table must parse to exactly the current series."""

    def setUp(self) -> None:
        self.rows = routing_table.load_table()

    def test_real_table_parses_all_rows(self) -> None:
        self.assertEqual(len(self.rows), 8)
        self.assertEqual(
            tuple(row.skill for row in self.rows),
            (
                "engineering-init",
                "engineering-process",
                "engineering-research",
                "engineering-routing",
                "engineering-sessions",
                "openhands-sessions",
                "openhands-watch",
                "skill-maker",
            ),
        )

    def test_enabled_and_registered_split(self) -> None:
        self.assertEqual(routing_table.routable_skills(self.rows), ENABLED)
        registered = tuple(row.skill for row in self.rows if row.state == "registered")
        self.assertEqual(registered, REGISTERED)

    def test_registered_rows_answer_skip(self) -> None:
        for name in REGISTERED:
            self.assertFalse(routing_table.should_route(name, self.rows), name)

    def test_enabled_rows_answer_routable(self) -> None:
        for name in ENABLED:
            self.assertTrue(routing_table.should_route(name, self.rows), name)

    def test_enabled_rows_carry_group_and_uses(self) -> None:
        by_name = {row.skill: row for row in self.rows}
        self.assertEqual(by_name["engineering-init"].group, "process")
        self.assertEqual(by_name["engineering-process"].group, "process")
        self.assertEqual(by_name["engineering-research"].group, "research")
        self.assertEqual(by_name["engineering-sessions"].group, "process")
        for name in ENABLED:
            self.assertEqual(by_name[name].uses, "engineering-routing", name)

    def test_registered_rows_carry_no_group_and_uses(self) -> None:
        by_name = {row.skill: row for row in self.rows}
        for name in REGISTERED:
            self.assertIsNone(by_name[name].group, name)
            self.assertIsNone(by_name[name].uses, name)

    def test_every_entry_exists_on_disk(self) -> None:
        for row in self.rows:
            self.assertTrue((ROOT / row.entry).is_dir(), row.entry)

    def test_default_path_is_the_real_repo_table(self) -> None:
        self.assertEqual(routing_table.ROOT, ROOT)
        self.assertTrue(routing_table.TABLE_PATH.is_file())
        self.assertEqual(routing_table.load_table(), self.rows)


class FabricatedTableTests(unittest.TestCase):
    """The failing direction must be proven non-vacuously, off-repo."""

    def load(self, body: str) -> tuple[routing_table.Row, ...]:
        """Load a fabricated table from a scratch tree.

        Args:
            body: Full Markdown text of the fabricated table.

        Returns:
            The parsed rows.
        """
        with tempfile.TemporaryDirectory() as directory:
            table = write_table(Path(directory), body)
            return routing_table.load_table(table)

    def assert_fails(self, body: str) -> None:
        with self.assertRaises(routing_table.RoutingTableError):
            self.load(body)

    def test_well_formed_fabricated_table_parses(self) -> None:
        body = _table(
            _row("engineering-pcb", "enabled", "hardware", "engineering-pcb",
                 "engineering-routing"),
            _row("engineering-notes", "registered", "—", "engineering-notes", "—"),
        )
        rows = self.load(body)
        self.assertEqual(len(rows), 2)
        self.assertEqual(routing_table.routable_skills(rows), ("engineering-pcb",))
        self.assertFalse(routing_table.should_route("engineering-notes", rows))

    def test_wrong_column_count_fails_closed(self) -> None:
        self.assert_fails(
            _table("| engineering-pcb | enabled | hardware | engineering-pcb |")
        )

    def test_unknown_state_fails_closed(self) -> None:
        self.assert_fails(
            _table(
                _row("engineering-pcb", "retired", "hardware", "engineering-pcb",
                     "engineering-routing")
            )
        )

    def test_unknown_group_fails_closed(self) -> None:
        self.assert_fails(
            _table(
                _row("engineering-pcb", "enabled", "ops", "engineering-pcb",
                     "engineering-routing")
            )
        )

    def test_duplicate_skill_fails_closed(self) -> None:
        self.assert_fails(
            _table(
                _row("engineering-pcb", "enabled", "hardware", "engineering-pcb",
                     "engineering-routing"),
                _row("engineering-pcb", "enabled", "hardware", "engineering-pcb",
                     "engineering-routing"),
            )
        )

    def test_entry_with_path_separator_fails_closed(self) -> None:
        self.assert_fails(
            _table(
                _row("engineering-pcb", "enabled", "hardware", "skills/engineering-pcb",
                     "engineering-routing")
            )
        )

    def test_unknown_skill_lookup_errors(self) -> None:
        body = _table(
            _row("engineering-pcb", "enabled", "hardware", "engineering-pcb",
                 "engineering-routing")
        )
        rows = self.load(body)
        with self.assertRaises(routing_table.RoutingTableError):
            routing_table.should_route("engineering-missing", rows)

    def test_empty_table_has_no_routable_skills(self) -> None:
        body = _table()
        rows = self.load(body)
        self.assertEqual(rows, ())
        self.assertEqual(routing_table.routable_skills(rows), ())

    def test_missing_table_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "routing-table.md"
            with self.assertRaises(routing_table.RoutingTableError):
                routing_table.load_table(missing)


if __name__ == "__main__":
    unittest.main()
