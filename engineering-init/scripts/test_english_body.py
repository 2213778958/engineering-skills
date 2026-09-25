#!/usr/bin/env python3
"""Guard: skill and doc bodies are English; Chinese lives only in allowed spots.

Allowed: frontmatter (trigger words), the ``## Terms`` tables of the three entry
skills, and quoted or backticked spans (user phrases, UI labels, runtime
literals). ``README.md`` and ``CONTEXT.md`` stay bilingual.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTRY_SKILLS = ("engineering-process", "engineering-routing", "engineering-init")
BILINGUAL = {"README.md", "CONTEXT.md"}
CJK = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")
TERMS = {
    "分发": "hand off",
    "决策": "decide",
    "推进": "advance",
    "职责表": "duty table",
    "回传": "report back",
    "开会话": "open a session",
}


def tracked(pattern: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", pattern], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [rel for rel in out.splitlines() if (ROOT / rel).is_file()]


def body_lines(rel: str) -> list[tuple[int, str]]:
    lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
    start = 0
    if rel.endswith(".md") and lines and lines[0] == "---":
        start = lines[1:].index("---") + 2
    return list(enumerate(lines[start:], start + 1))


def terms_rows(rel: str) -> dict[str, str]:
    text = (ROOT / rel).read_text(encoding="utf-8")
    section = text.split("\n## Terms\n", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("| ") and "---" not in line]
    return {cells[0]: cells[1] for cells in (
        [cell.strip() for cell in row.strip("|").split("|")] for row in rows[1:]
    )}


def stray(line: str) -> bool:
    line = re.sub(r"`[^`]*`", "", line)
    line = re.sub(r'"[^"]*"', "", line)
    return bool(CJK.search(line))


class EnglishBodyTests(unittest.TestCase):
    def test_markdown_bodies_have_no_stray_chinese(self) -> None:
        bad = []
        for rel in tracked("*.md"):
            if rel in BILINGUAL:
                continue
            in_terms = False
            for number, line in body_lines(rel):
                if line.startswith("## "):
                    in_terms = line == "## Terms" and rel.split("/")[0] in ENTRY_SKILLS
                if in_terms and line.startswith("| "):
                    continue
                if stray(line):
                    bad.append(f"{rel}:{number}: {line}")
        self.assertEqual(bad, [])

    def test_python_has_no_stray_chinese(self) -> None:
        bad = [
            f"{rel}:{number}: {line}"
            for rel in tracked("*.py")
            for number, line in body_lines(rel)
            if stray(line)
        ]
        self.assertEqual(bad, [])

    def test_entry_skills_share_the_terms_table(self) -> None:
        for skill in ENTRY_SKILLS:
            self.assertEqual(terms_rows(f"{skill}/SKILL.md"), TERMS, skill)

    def test_context_glossary_lists_every_term(self) -> None:
        context = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        for zh, en in TERMS.items():
            self.assertIn(f"**{zh}** = {en}", context)


if __name__ == "__main__":
    unittest.main()
