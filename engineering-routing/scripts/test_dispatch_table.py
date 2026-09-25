#!/usr/bin/env python3
"""Guard: the dispatch table owns decisions; research staffing is one rule.

``engineering-routing/SKILL.md`` holds the **dispatch table** (task type →
stay / dispatch / delegate). It is distinct from the **routing table**
``references/routing-table.md`` (which skills are routable, ADR 0007). Callers
hand unconfirmed decisions to routing, so the dispatch table carries the
decision row and is the only place in routing that names ``grilling``.
Research is staffed by the delivery, acceptance or planning manage; human and
arbitration never staff it.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "engineering-routing" / "SKILL.md"
RESEARCH = ROOT / "engineering-research" / "SKILL.md"
PROCESS = ROOT / "engineering-process"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def dispatch_rows(text: str) -> list[str]:
    section = text.split("## Dispatch table", 1)[1].split("\n## ", 1)[0]
    return [line for line in section.splitlines() if line.startswith("| ") and "---" not in line]


def repo_docs() -> list[Path]:
    return [
        path
        for path in sorted(ROOT.rglob("*.md"))
        if "docs" not in path.relative_to(ROOT).parts[:1]
        and ".git" not in path.parts
    ]


class DispatchTableTests(unittest.TestCase):
    def test_heading_is_dispatch_table(self) -> None:
        text = read(SKILL)
        self.assertIn("\n## Dispatch table\n", text)
        self.assertNotRegex(text, r"\n## Table\n")

    def test_decision_row_stays_and_runs_grilling(self) -> None:
        rows = [row for row in dispatch_rows(read(SKILL)) if row.startswith("| Unconfirmed decision")]
        self.assertEqual(len(rows), 1)
        self.assertIn("| stay |", rows[0])
        self.assertIn("`grilling`", rows[0])

    def test_grilling_only_in_dispatch_table(self) -> None:
        text = read(SKILL)
        rows = "\n".join(dispatch_rows(text))
        self.assertEqual(text.count("grilling"), rows.count("grilling"))

    def test_dispatch_table_is_not_called_routing_table(self) -> None:
        self.assertIn("The dispatch table (task type → link) is not the routing table", read(SKILL))
        stub = read(ROOT / "engineering-init" / "references" / "models-stub.md")
        self.assertIn("`engineering-routing` dispatch table", stub)
        for doc in repo_docs():
            self.assertNotRegex(read(doc), r"(?:the|use the) table below", doc.relative_to(ROOT))


class ResearchStaffingTests(unittest.TestCase):
    STAFFING = re.compile(r"any department's \*{0,2}manage\*{0,2} may staff|staffable by any department")

    def test_no_any_department_staffing(self) -> None:
        for doc in repo_docs():
            self.assertIsNone(self.STAFFING.search(read(doc)), doc.relative_to(ROOT))

    def test_research_names_the_staffing_departments(self) -> None:
        text = read(RESEARCH)
        for dept in ("**delivery**", "**acceptance**", "**planning**"):
            self.assertIn(dept, text)
        self.assertIn("**human** and **arbitration** do not staff research", text)
        self.assertIn("Planning-staffed research", text)

    def test_process_rules_agree(self) -> None:
        rules = read(PROCESS / "references" / "rules.md")
        self.assertIn("staffs only `planning implement` / `planning review` / `research`", rules)
        self.assertNotIn("arbitration / research from planning", rules)
        self.assertEqual(rules.count("delivery, acceptance or planning manage"), 2)
        templates = read(PROCESS / "references" / "templates.md")
        self.assertIn("human and arbitration do not", templates)
        hops = read(PROCESS / "references" / "hops.md")
        self.assertIn("no research staffing", hops)

    def test_routing_planning_decide_may_staff_research(self) -> None:
        self.assertIn("and `research` when planning needs research input", read(SKILL))


if __name__ == "__main__":
    unittest.main()
