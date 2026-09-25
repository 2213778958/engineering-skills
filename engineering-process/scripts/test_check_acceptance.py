#!/usr/bin/env python3
"""Offline tests for check_acceptance.py on throwaway git repositories."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_acceptance  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class Repo:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str) -> str:
        out = subprocess.run(["git", *args], cwd=self.path, capture_output=True, text=True, check=True)
        return out.stdout.strip()

    def commit(self, name: str) -> str:
        (self.path / name).write_text(name, encoding="utf-8")
        self.git("add", name)
        self.git("commit", "-q", "-m", name)
        return self.git("rev-parse", "HEAD")

    def publish(self, branch: str) -> None:
        self.git("update-ref", f"refs/remotes/origin/{branch}", branch)


def run(repo: Repo, *argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = check_acceptance.main([*argv, "--repo", str(repo.path)])
    return code, buffer.getvalue()


class CheckAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self.tmp.name))
        self.repo.commit("base")
        self.repo.publish("main")
        self.repo.git("switch", "-q", "-c", "feat/1-a")
        self.repo.commit("a1")
        self.repo.publish("feat/1-a")
        self.repo.git("switch", "-q", "-c", "fix/2-b")
        self.repo.commit("b1")
        self.repo.publish("fix/2-b")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pre_passes_when_head_covers_stacked_tickets(self) -> None:
        code, out = run(self.repo, "pre", "--head", "origin/fix/2-b", "--tickets", "1", "2")
        self.assertEqual(code, 0, out)
        self.assertIn("pre: pass", out)

    def test_pre_fails_when_ticket_has_no_branch(self) -> None:
        code, out = run(self.repo, "pre", "--head", "origin/fix/2-b", "--tickets", "1", "2", "3")
        self.assertEqual(code, 1)
        self.assertIn("FAIL #3: no origin/feat/3-* or origin/fix/3-* branch", out)

    def test_pre_fails_when_head_misses_a_stacked_branch(self) -> None:
        code, out = run(self.repo, "pre", "--head", "origin/feat/1-a", "--tickets", "1", "2")
        self.assertEqual(code, 1)
        self.assertIn("FAIL #2: origin/fix/2-b is not an ancestor of origin/feat/1-a", out)

    def test_pre_fails_on_commits_outside_the_tickets(self) -> None:
        self.repo.git("switch", "-q", "-c", "merge/9")
        self.repo.commit("next-version")
        code, out = run(self.repo, "pre", "--head", "merge/9", "--tickets", "1", "2")
        self.assertEqual(code, 1)
        self.assertIn("next-version is not on any ticket branch", out)

    def test_pre_allows_merge_commits_joining_ticket_branches(self) -> None:
        self.repo.git("switch", "-q", "-c", "feat/3-c", "main")
        self.repo.commit("c1")
        self.repo.publish("feat/3-c")
        self.repo.git("switch", "-q", "-c", "merge/9", "fix/2-b")
        self.repo.git("merge", "-q", "--no-ff", "-m", "merge feat/3-c", "feat/3-c")
        code, out = run(self.repo, "pre", "--head", "merge/9", "--tickets", "1", "2", "3")
        self.assertEqual(code, 0, out)

    def test_pre_fails_when_a_ticket_has_several_branches(self) -> None:
        self.repo.git("branch", "fix/1-again", "feat/1-a")
        self.repo.publish("fix/1-again")
        code, out = run(self.repo, "pre", "--head", "origin/fix/2-b", "--tickets", "1", "2")
        self.assertEqual(code, 1)
        self.assertIn("FAIL #1: several branches", out)

    def test_post_fails_before_merge_and_passes_after_merge_commit(self) -> None:
        code, out = run(self.repo, "post", "--tickets", "1", "2")
        self.assertEqual(code, 1)
        self.assertIn("FAIL #1: origin/feat/1-a is not an ancestor of origin/main", out)
        self.repo.git("switch", "-q", "main")
        self.repo.git("merge", "-q", "--no-ff", "-m", "Merge PR", "fix/2-b")
        self.repo.publish("main")
        code, out = run(self.repo, "post", "--tickets", "1", "2")
        self.assertEqual(code, 0, out)
        self.assertIn("post: pass", out)

    def test_post_fails_after_squash_merge(self) -> None:
        self.repo.git("switch", "-q", "main")
        self.repo.git("merge", "-q", "--squash", "fix/2-b")
        self.repo.git("commit", "-q", "-m", "squash")
        self.repo.publish("main")
        code, _ = run(self.repo, "post", "--tickets", "1", "2")
        self.assertEqual(code, 1)

    def test_missing_default_branch_fails(self) -> None:
        code, out = run(self.repo, "post", "--tickets", "1", "--default", "trunk")
        self.assertEqual(code, 1)
        self.assertIn("origin/trunk not found", out)


class AcceptanceHopTests(unittest.TestCase):
    def test_hop_runs_the_guard(self) -> None:
        hops = (ROOT / "engineering-process" / "references" / "hops.md").read_text(encoding="utf-8")
        section = hops.split("## 3e.", 1)[1]
        self.assertIn("check_acceptance.py pre", section)
        self.assertIn("check_acceptance.py post", section)
        self.assertIn("merge commit", section)
        self.assertNotIn("confirm the default branch contains the commits → close this acceptance", section)


if __name__ == "__main__":
    unittest.main()
