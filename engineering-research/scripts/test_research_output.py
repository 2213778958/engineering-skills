#!/usr/bin/env python3
"""Guard: research delivers one research directory; raw materials live outside git.

ADR 0008: every research call delivers ``docs/research/<YYYY-MM>-<slug>/``
entered through its ``README.md``; raw files live in ``resources/`` beside
``master/`` and are referenced as ``resources:<path>`` through the committed
manifest ``docs/research/resources.md``. Headers are written downstream by the
delivery implement. This module asserts the research docs and their callers
agree on that contract.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "engineering-research" / "SKILL.md"
LAYOUT = ROOT / "engineering-research" / "references" / "layout.md"
HEADERS = ROOT / "engineering-research" / "references" / "headers.md"
ADR = ROOT / "docs" / "adr" / "0008-research-output-directory.md"
MANIFEST_HEADER = "| path | source URL | fetched | license | size | sha256 |"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ResearchContractTests(unittest.TestCase):
    def test_skill_delivers_a_research_directory(self) -> None:
        text = read(SKILL)
        self.assertIn("docs/research/<YYYY-MM>-<slug>/", text)
        self.assertIn("docs/research/README.md", text)
        self.assertIn("docs/research/resources.md", text)
        self.assertIn("resources:", text)

    def test_skill_links_its_references(self) -> None:
        text = read(SKILL)
        for ref in ("references/layout.md", "references/headers.md"):
            self.assertIn(f"]({ref})", text)
            self.assertTrue((SKILL.parent / ref).is_file(), ref)

    def test_skill_splits_faces_and_synthesizes(self) -> None:
        text = read(SKILL)
        self.assertIn("## Faces", text)
        self.assertIn("**Synthesize.**", text)
        self.assertIn("(≤3)", text)

    def test_skill_input_failure_rules(self) -> None:
        text = read(SKILL)
        self.assertIn("`Result: fail` + `Missing: <fields>`", text)
        self.assertIn("Material not found → not an input failure", text)

    def test_research_does_not_write_headers(self) -> None:
        text = read(SKILL)
        self.assertNotRegex(text, r"Headers written|writes? (?:the )?header files into")
        self.assertIn("Do not write drivers or headers", text)
        self.assertIn("Research does not write headers", read(HEADERS))
        self.assertIn("**delivery implement**", read(HEADERS))


class LayoutTests(unittest.TestCase):
    def test_resources_sit_beside_master_outside_git(self) -> None:
        text = read(LAYOUT)
        self.assertIn("beside `master/` and `worktree/`", text)
        self.assertIn("Never `git add` a file under `resources/`", text)

    def test_resolution_order(self) -> None:
        text = read(LAYOUT)
        env = text.index("`ENGINEERING_RESOURCES`")
        walk = text.index("walk up the parents")
        self.assertLess(env, walk)

    def test_manifest_columns(self) -> None:
        self.assertIn(MANIFEST_HEADER, read(LAYOUT))

    def test_research_directory_is_markdown_only(self) -> None:
        self.assertIn("Markdown only", read(LAYOUT))


class CallerAgreementTests(unittest.TestCase):
    def test_routing_row_names_research_directory(self) -> None:
        text = read(ROOT / "engineering-routing" / "SKILL.md")
        row = next(line for line in text.splitlines() if line.startswith("| **research** |"))
        self.assertIn("research directory", row)

    def test_models_stub_row_names_docs_research(self) -> None:
        text = read(ROOT / "engineering-init" / "references" / "models-stub.md")
        row = next(line for line in text.splitlines() if line.startswith("| research | employee |"))
        self.assertIn("`docs/research/`", row)
        self.assertNotIn("headers included", row)

    def test_headers_are_written_downstream(self) -> None:
        contract = read(ROOT / "engineering-init" / "references" / "contract.md")
        self.assertIn("delivery implement writes the headers from the research findings", contract)
        hops = read(ROOT / "engineering-process" / "references" / "hops.md")
        self.assertIn("headers are written by delivery implement from the findings", hops)

    def test_no_caller_says_extract_headers(self) -> None:
        pattern = re.compile(r"[Ee]xtract headers|datasheet headers included")
        for skill in ("engineering-init", "engineering-process", "engineering-routing"):
            for doc in sorted((ROOT / skill).rglob("*.md")):
                self.assertIsNone(pattern.search(read(doc)), doc.relative_to(ROOT))

    def test_adr_records_the_decision(self) -> None:
        text = read(ADR)
        self.assertIn("Supersedes the output part of ADR 0006", text)
        self.assertIn("`resources:<path>`", text)


if __name__ == "__main__":
    unittest.main()
