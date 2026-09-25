#!/usr/bin/env python3
"""Guard: skill and doc bodies are English; Chinese lives only in allowed spots.

Allowed in Markdown: frontmatter (trigger words), the ``## Terms`` tables of
the three entry skills, backticked literals, user-phrase examples inside
``(e.g. ...)``, and the UI labels in ``UI_LABELS``. User phrases are examples of
an intent, never the condition. Python allows double-quoted string
literals (runtime markers, fixtures). ``README.md`` and ``CONTEXT.md`` stay bilingual.
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
UI_LABELS = {"无工作区"}
EXAMPLES = re.compile(r"\(e\.g\. [^)]*\)")
LITERAL_PHRASE = re.compile(r'User (?:said|typed|commands|asked) "')


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


def stray(line: str, markdown: bool) -> bool:
    line = re.sub(r"`[^`]*`", "", line)
    if markdown:
        line = EXAMPLES.sub("", line)
        line = re.sub(r'"([^"]*)"', lambda m: "" if m.group(1) in UI_LABELS else m.group(0), line)
    else:
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
                if stray(line, markdown=True):
                    bad.append(f"{rel}:{number}: {line}")
        self.assertEqual(bad, [])

    def test_python_has_no_stray_chinese(self) -> None:
        bad = [
            f"{rel}:{number}: {line}"
            for rel in tracked("*.py")
            for number, line in body_lines(rel)
            if stray(line, markdown=False)
        ]
        self.assertEqual(bad, [])

    def test_intent_not_literal_phrases(self) -> None:
        bad = [
            f"{rel}:{number}"
            for rel in tracked("*.md")
            if rel not in BILINGUAL
            for number, line in body_lines(rel)
            if LITERAL_PHRASE.search(line)
        ]
        self.assertEqual(bad, [])
        supervise = (ROOT / "engineering-process" / "references" / "supervise.md").read_text(encoding="utf-8")
        self.assertIn("**Advance request** = the user asks to move the project forward", supervise)
        self.assertIn("Judge by intent, not wording; unclear → ask.", supervise)
        routing = (ROOT / "engineering-routing" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("The user asks for a separate conversation window (e.g.", routing)
        self.assertIn("Judge these by intent, not wording. Unclear → ask the user.", routing)

    def test_entry_skills_share_the_terms_table(self) -> None:
        for skill in ENTRY_SKILLS:
            self.assertEqual(terms_rows(f"{skill}/SKILL.md"), TERMS, skill)

    def test_context_glossary_lists_every_term(self) -> None:
        context = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        for zh, en in TERMS.items():
            self.assertIn(f"**{zh}** = {en}", context)


if __name__ == "__main__":
    unittest.main()
