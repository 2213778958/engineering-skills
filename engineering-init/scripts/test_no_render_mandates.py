#!/usr/bin/env python3
"""Guard: the DAG rendering mechanism stays cancelled across active files.

Ticket #47 removed the render_graph.py mechanism; ordering now comes only
from GitHub-native relationships (sub-issue parent + blockedBy). This guard
keeps render mandates, graph-test wiring, and hard imports from returning.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MANDATE_MARKERS = ("render_graph.py", "render_graph_refs")
GRAPH_TEST_MARKERS = ("test_render_graph_refs.py", "test_render_graph_refs")
FORBIDDEN_MARKER_FILES: tuple[Path, ...] = (
    ROOT / "AGENTS.md",
    ROOT / "engineering-init" / "SKILL.md",
    *sorted((ROOT / "engineering-process").rglob("*.md")),
)
SCANNED_SUFFIXES = {".md", ".py"}


def iter_repo_files() -> list[Path]:
    """Return every allowlist-relevant text file eligible for import scans."""
    scripts = ROOT / "engineering-init" / "scripts"
    files = [
        path
        for path in scripts.rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    process = ROOT / "engineering-process"
    if process.is_dir():
        files.extend(path for path in process.rglob("*.py"))
    return sorted(files)


def relative(path: Path) -> str:
    """Return the repo-relative POSIX path for error messages."""
    return path.relative_to(ROOT).as_posix()


class RenderMandateTests(unittest.TestCase):
    """No active rule file may mandate or mention the cancelled renderer."""

    def test_deleted_scripts_are_gone(self) -> None:
        for name in (
            "engineering-init/scripts/render_graph.py",
            "engineering-init/scripts/test_render_graph_refs.py",
        ):
            self.assertFalse((ROOT / name).exists(), name)

    def test_no_render_mandates_in_rule_files(self) -> None:
        """No file under the active skills may mandate the cancelled renderer."""
        active_files: list[Path] = []
        for skill in ("engineering-process", "engineering-init", "skill-maker"):
            root = ROOT / skill
            if root.is_dir():
                active_files.extend(sorted(root.rglob("*.md")))
        active_files.append(ROOT / "AGENTS.md")
        offenders = []
        for path in active_files:
            text = path.read_text(encoding="utf-8")
            for marker in MANDATE_MARKERS:
                if marker in text:
                    offenders.append(f"{relative(path)}: {marker}")
        self.assertEqual(offenders, [])

    def test_no_hard_imports_of_render_graph(self) -> None:
        offenders = []
        for path in iter_repo_files():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    if name.split(".")[0] == "render_graph":
                        offenders.append(f"{relative(path)}: import {name}")
        self.assertEqual(offenders, [])

    def test_no_render_graph_literal_usage(self) -> None:
        offenders = []
        for path in iter_repo_files():
            text = path.read_text(encoding="utf-8")
            if "render_graph" in text and path.name != Path(__file__).name:
                offenders.append(relative(path))
        self.assertEqual(offenders, [])


class GraphTestWiringTests(unittest.TestCase):
    """The verify pipeline must no longer reference the deleted graph tests."""

    def test_no_graph_test_references_in_verify_stages(self) -> None:
        text = (ROOT / "engineering-init" / "scripts" / "verify.py").read_text(
            encoding="utf-8"
        )
        offenders = [m for m in GRAPH_TEST_MARKERS if m in text]
        self.assertEqual(offenders, [])

    def test_no_graph_test_references_in_agents_md(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        offenders = [m for m in GRAPH_TEST_MARKERS if m in text]
        self.assertEqual(offenders, [])


class VerifyStagesTests(unittest.TestCase):
    """The verify STAGES entry must cover exactly the surviving stages."""

    def test_verify_stage_targets_test_verify(self) -> None:
        sys.path.insert(0, str(ROOT / "engineering-init" / "scripts"))
        try:
            import verify

            stages = dict(verify.STAGES)
            self.assertIn("watch", stages)
            self.assertIn("verify", stages)
            self.assertIn("guard", stages)
            self.assertNotIn("render_graph_refs", stages)
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
