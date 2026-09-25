#!/usr/bin/env python3
"""Guard: research delivers one research directory outside the code repo.

ADR 0008 (revised by #78): every research call delivers
``research:<YYYY-MM>-<slug>/<slug>.md`` in the external ``research/`` library
beside ``master/``; raw files live in ``resources/`` and are listed in
``research:resources.md``. The code repo never receives research files; when
``research/`` is a git repo (GitHub Wiki) only the synthesis subagent pushes
it. Headers are written downstream by the delivery implement.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "engineering-research" / "SKILL.md"
LAYOUT = ROOT / "engineering-research" / "references" / "layout.md"
ADR = ROOT / "docs" / "adr" / "0008-research-output-directory.md"
MANIFEST_HEADER = "| path | source URL | fetched | license | size | sha256 |"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def tracked_docs() -> list[Path]:
    """Tracked Markdown except ADRs (they keep history)."""
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [
        ROOT / rel
        for rel in out.splitlines()
        if not rel.startswith("docs/adr/") and (ROOT / rel).is_file()
    ]


class ResearchContractTests(unittest.TestCase):
    def test_skill_delivers_an_external_research_directory(self) -> None:
        text = read(SKILL)
        self.assertIn("`research:<YYYY-MM>-<slug>/<slug>.md`", text)
        self.assertIn("never inside the code repo", text)
        self.assertIn("`research:Home.md`", text)
        self.assertIn("`research:resources.md`", text)

    def test_skill_links_its_references(self) -> None:
        text = read(SKILL)
        self.assertIn("](references/layout.md)", text)
        self.assertTrue((SKILL.parent / "references" / "layout.md").is_file())
        self.assertFalse((SKILL.parent / "references" / "headers.md").exists())
        self.assertNotIn("headers.md", text)

    def test_skill_splits_faces_and_synthesizes(self) -> None:
        text = read(SKILL)
        self.assertIn("## Faces", text)
        self.assertNotIn("## Chip-interface face", text)
        self.assertNotIn("chip-interface face", text)
        faces = text.split("## Faces", 1)[1].split("\n## ", 1)[0]
        types = re.findall(r"^\| `(\w+)` \|", faces, flags=re.M)
        self.assertEqual(
            types, ["approach", "options", "library", "assets", "api", "standard", "chip", "facts"]
        )
        self.assertIn("a face whose type needs a primary document (Faces table)", text)
        self.assertIn("`chip` findings → the delivery implement writes headers per the repo's header conventions", text)
        self.assertIn("**Synthesize.**", text)
        self.assertIn("(≤3)", text)

    def test_skill_input_failure_rules(self) -> None:
        text = read(SKILL)
        self.assertIn("`Result: fail` + `Missing: <fields>`", text)
        self.assertIn("`Missing: ENGINEERING_RESEARCH`", text)
        self.assertIn("`Missing: ENGINEERING_RESOURCES`", text)
        self.assertIn("Material not found → not an input failure", text)

    def test_research_does_not_write_headers(self) -> None:
        text = read(SKILL)
        self.assertNotRegex(text, r"Headers written|writes? (?:the )?header files into")
        self.assertIn("Do not write drivers or headers", text)
        conventions = read(ROOT / "engineering-init" / "references" / "conventions.md")
        self.assertIn("do not invent registers or typical values", conventions)

    def test_sync_pushes_only_the_research_repo(self) -> None:
        text = read(SKILL)
        self.assertIn("the code repo never receives research files", text)
        self.assertIn("the synthesis subagent commits and pushes that repo only", text)
        self.assertIn("no commit, no push", text)

    def test_subagent_prompts_carry_rules_10_fields(self) -> None:
        text = read(SKILL)
        self.assertIn("ticket-tree `cd` path first (planning-staffed: `master/`)", text)
        self.assertIn("(planning-staffed: the ticket being decided, else `none`)", text)

    def test_manage_does_not_write_research_files(self) -> None:
        text = read(SKILL)
        self.assertIn("never by the manage window", text)
        self.assertIn("synthesis subagent", text)


class LayoutTests(unittest.TestCase):
    def test_libraries_sit_beside_master_outside_the_repo(self) -> None:
        text = read(LAYOUT)
        self.assertIn("beside `master/` and `worktree/` in the container folder, outside the code repo", text)
        self.assertIn("Never `git add` a file under `resources/`", text)

    def test_wiki_unique_names(self) -> None:
        text = read(LAYOUT)
        self.assertIn("File names are unique across the whole library", text)
        self.assertIn("`<slug>--<face>.md`", text)
        self.assertIn("Never a bare `README.md`", text)

    def test_wiki_sync(self) -> None:
        text = read(LAYOUT)
        self.assertIn("| [[<slug>]] | research:<YYYY-MM>-<slug>/<slug>.md |", text)
        self.assertIn(".wiki.git research", text)
        self.assertIn("the only push a research employee makes", text)

    def test_resolution_order(self) -> None:
        text = read(LAYOUT)
        self.assertLess(text.index("`ENGINEERING_RESEARCH`"), text.index("walk up the parents"))
        self.assertIn("`Missing: <VAR>`", text)

    def test_manifest(self) -> None:
        text = read(LAYOUT)
        self.assertIn(MANIFEST_HEADER, text)
        self.assertIn("Only the synthesis subagent writes this file", text)

    def test_research_library_is_markdown_only(self) -> None:
        self.assertIn("Markdown only", read(LAYOUT))


class CallerAgreementTests(unittest.TestCase):
    def test_no_in_repo_research_directory(self) -> None:
        stale = re.compile(r"docs/research|findings/|synthesis commit")
        for doc in tracked_docs():
            self.assertIsNone(stale.search(read(doc)), doc.relative_to(ROOT))

    def test_routing_row_names_research_directory(self) -> None:
        text = read(ROOT / "engineering-routing" / "SKILL.md")
        row = next(line for line in text.splitlines() if line.startswith("| **research** |"))
        self.assertIn("research directory", row)

    def test_models_stub_row_names_external_library(self) -> None:
        text = read(ROOT / "engineering-init" / "references" / "models-stub.md")
        row = next(line for line in text.splitlines() if line.startswith("| research | employee |"))
        self.assertIn("external `research/` library", row)

    def test_push_exception_is_the_research_repo_only(self) -> None:
        rules = read(ROOT / "engineering-process" / "references" / "rules.md")
        self.assertIn("Only exception: the research synthesis subagent pushes the external `research/` git repo", rules)
        supervise = read(ROOT / "engineering-process" / "references" / "supervise.md")
        self.assertIn("except research synthesis → external `research/` repo", supervise)
        self.assertIn("do not push the code repo's default branch |", rules)
        conventions = read(ROOT / "engineering-init" / "references" / "conventions.md")
        self.assertIn("the research synthesis subagent pushes the external `research/` repo", conventions)
        templates = read(ROOT / "engineering-process" / "references" / "templates.md")
        self.assertIn("The research synthesis subagent may push the external `research/` repo only", templates)
        self.assertIn("do not git push the code repo; push only the `research/` repo", read(SKILL))

    def test_downstream_reads_research_path(self) -> None:
        hops = read(ROOT / "engineering-process" / "references" / "hops.md")
        self.assertIn("names its `research:` entry path as read-only input (headers", hops)
        self.assertIn("Planning needs research input", hops)
        contract = read(ROOT / "engineering-init" / "references" / "contract.md")
        self.assertIn("delivery implement writes the headers from the research findings", contract)

    def test_no_caller_says_extract_headers(self) -> None:
        pattern = re.compile(
            r"[Ee]xtract headers|datasheet headers included|抽寄存器头文件|交一份调研文档"
        )
        for doc in tracked_docs():
            self.assertIsNone(pattern.search(read(doc)), doc.relative_to(ROOT))

    def test_adr_records_the_decision(self) -> None:
        text = read(ADR)
        self.assertIn("Revised before the v0.1 tag by #78", text)
        self.assertIn("Supersedes the output part of ADR 0006", text)
        self.assertIn("`research:<path>` and `resources:<path>`", text)


if __name__ == "__main__":
    unittest.main()
