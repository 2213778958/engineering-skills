#!/usr/bin/env python3
"""Tests: engineering-init's registry gate routes enabled, stops registered.

The real repository table must gate exactly the registered series (ADR 0007:
the table is data; this module is a read-only consumer of the routing-table
primitives). The fabricated-tree direction proves the skip is non-vacuous,
off-repo: a registered row stops at the gate with the gate branch provably
not taken, an unknown skill and a malformed table fail closed, and a missing
entry directory is rejected.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "engineering-routing" / "scripts"))

import routing_registry as registry
import routing_table

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


def write_scratch(
    root: Path, body: str, entry_name: str | None = "engineering-pcb"
) -> Path:
    """Write a fabricated table and its entry directory into a scratch tree.

    Args:
        root: Scratch root receiving the fabricated skill tree.
        body: Full Markdown text of the fabricated table.
        entry_name: Contains-node directory to create under the root, or
            ``None`` to leave the entry missing on disk.

    Returns:
        Path of the written table file.
    """
    (root / "engineering-routing" / "references").mkdir(parents=True)
    if entry_name is not None:
        (root / entry_name).mkdir()
    table = root / "engineering-routing" / "references" / "routing-table.md"
    table.write_text(body, encoding="utf-8")
    return table


class RepoRegistryGateTests(unittest.TestCase):
    """The real repo table must gate exactly the current series."""

    def setUp(self) -> None:
        self.rows = registry.rows()

    def test_real_table_parses_eight_rows(self) -> None:
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
        self.assertEqual(registry.enabled_skills(self.rows), ENABLED)
        self.assertEqual(
            tuple(row.skill for row in registry.registered_skills(self.rows)),
            REGISTERED,
        )

    def test_require_routable_returns_enabled_row(self) -> None:
        row = registry.require_routable("engineering-init")
        self.assertEqual(row.skill, "engineering-init")
        self.assertEqual(row.state, "enabled")
        self.assertEqual(row.entry, "engineering-init")

    def test_registered_rows_stop_at_the_gate(self) -> None:
        for name in REGISTERED:
            with self.assertRaises(registry.RegistryGateError) as caught:
                registry.require_routable(name, self.rows)
            self.assertIn("registered, not enabled", str(caught.exception), name)
            self.assertIn("patch ticket", str(caught.exception), name)

    def test_is_routable_agrees_with_routing_table(self) -> None:
        for row in self.rows:
            self.assertEqual(
                registry.is_routable(row.skill, self.rows),
                routing_table.should_route(row.skill, self.rows),
                row.skill,
            )

    def test_require_entry_returns_existing_directory(self) -> None:
        for row in self.rows:
            entry = registry.require_entry(row.skill, self.rows)
            self.assertEqual(entry, ROOT / row.entry, row.skill)
            self.assertTrue(entry.is_dir(), row.skill)

    def test_defaults_load_the_real_repo_table(self) -> None:
        self.assertTrue(registry.TABLE_PATH.is_file())
        self.assertEqual(registry.rows(), self.rows)
        self.assertEqual(registry.enabled_skills(), ENABLED)


class FabricatedGateTests(unittest.TestCase):
    """The skip direction must be proven non-vacuously, off-repo."""

    def gate(self, body: str, entry_name: str | None = "engineering-pcb") -> None:
        """Run the gate flow against a fabricated table in a scratch tree.

        Args:
            body: Full Markdown text of the fabricated table.
            entry_name: Contains-node directory to create, or ``None`` to
                leave the entry missing on disk.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            table = write_scratch(root, body, entry_name)
            rows = routing_table.load_table(table)
            with self.assertRaises(registry.RegistryGateError):
                registry.require_routable("engineering-notes", rows)
            self.assertFalse(registry.is_routable("engineering-notes", rows))

    def test_registered_row_skips_gate_branch(self) -> None:
        body = _table(
            _row(
                "engineering-pcb",
                "enabled",
                "hardware",
                "engineering-pcb",
                "engineering-routing",
            ),
            _row("engineering-notes", "registered", "—", "engineering-notes", "—"),
        )
        self.gate(body)

    def test_unknown_skill_fails_closed(self) -> None:
        body = _table(
            _row(
                "engineering-pcb",
                "enabled",
                "hardware",
                "engineering-pcb",
                "engineering-routing",
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            table = write_scratch(Path(directory), body)
            rows = routing_table.load_table(table)
            with self.assertRaises(routing_table.RoutingTableError):
                registry.require_routable("engineering-missing", rows)
            with self.assertRaises(routing_table.RoutingTableError):
                registry.is_routable("engineering-missing", rows)

    def test_malformed_table_fails_closed_through_gate(self) -> None:
        body = _table("| engineering-pcb | enabled | hardware | engineering-pcb |")
        with tempfile.TemporaryDirectory() as directory:
            table = write_scratch(Path(directory), body)
            with self.assertRaises(routing_table.RoutingTableError):
                routing_table.load_table(table)

    def test_malformed_row_rejected_through_require_routable(self) -> None:
        body = _table(
            _row("engineering-pcb", "enabled", "hardware", "engineering-pcb", "extra")
        )
        with tempfile.TemporaryDirectory() as directory:
            table = write_scratch(Path(directory), body)
            with self.assertRaises(routing_table.RoutingTableError):
                registry.require_routable(
                    "engineering-pcb", routing_table.load_table(table)
                )

    def test_missing_entry_directory_raises_gate_error(self) -> None:
        body = _table(
            _row(
                "engineering-pcb",
                "enabled",
                "hardware",
                "engineering-pcb",
                "engineering-routing",
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            table = write_scratch(Path(directory), body, entry_name=None)
            rows = routing_table.load_table(table)
            self.assertTrue(registry.is_routable("engineering-pcb", rows))
            with self.assertRaises(registry.RegistryGateError):
                registry.require_entry("engineering-pcb", rows)


if __name__ == "__main__":
    unittest.main()
