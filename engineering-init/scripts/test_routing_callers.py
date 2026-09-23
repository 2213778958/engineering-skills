#!/usr/bin/env python3
"""Guard: wired callers point at the routing-table registry, not lists.

The routing registry is pure data in
``engineering-routing/references/routing-table.md`` (ADR 0006 Decision 1).
Callers must reference that table (or defer to ``engineering-routing``,
which reads it) instead of hard-coding a skill dispatch list. This module
asserts the caller wiring and that every enabled table entry exists on disk.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "engineering-routing" / "scripts"))

import routing_table

TABLE_REF = "engineering-routing/references/routing-table.md"
CALLERS = (
    "engineering-init/SKILL.md",
    "datasheet-headers/SKILL.md",
    "openhands-sessions/SKILL.md",
)


class CallerWiringTests(unittest.TestCase):
    def test_callers_reference_routing_table(self) -> None:
        for caller in CALLERS:
            text = (ROOT / caller).read_text(encoding="utf-8")
            self.assertIn(TABLE_REF, text, caller)

    def test_callers_state_enabled_rules_registered(self) -> None:
        for caller in CALLERS:
            text = (ROOT / caller).read_text(encoding="utf-8")
            self.assertIn(TABLE_REF, text, caller)
            for phrase in ("routing-table.md", "registered"):
                self.assertIn(phrase, text, caller)
            self.assertRegex(
                text, r"`(?:\.\./)?engineering-routing/references/routing-table\.md`"
            )

    def test_process_staffs_through_read_and_run_routing(self) -> None:
        docs = [ROOT / "engineering-process" / "SKILL.md"]
        docs.extend((ROOT / "engineering-process" / "references").glob("*.md"))
        pattern = re.compile(
            r"(?:read(?:ing)? and run(?:ning)?|staff(?:ing)? [^\n]*? by reading"
            r" and running) `engineering-routing`"
        )
        matches = [
            doc.relative_to(ROOT)
            for doc in docs
            if pattern.search(doc.read_text(encoding="utf-8"))
        ]
        self.assertTrue(matches, "no engineering-process doc staffs via routing")
        for doc in matches:
            self.assertNotIn(
                "engineering-routing/scripts/routing_table.py",
                doc.read_text(encoding="utf-8"),
                doc,
            )


class RoutingTableEntryTests(unittest.TestCase):
    def test_table_loads(self) -> None:
        self.assertTrue(routing_table.load_table())

    def test_enabled_entries_exist_on_disk(self) -> None:
        for row in routing_table.load_table():
            if row.state != "enabled":
                continue
            self.assertTrue((ROOT / row.entry).is_dir(), row.entry)


if __name__ == "__main__":
    unittest.main()
