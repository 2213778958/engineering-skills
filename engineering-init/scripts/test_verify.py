#!/usr/bin/env python3
"""Smoke tests for the verify runner: stage plumbing over synthetic commands."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify

ROOT = Path(__file__).resolve().parents[2]


class StagesTests(unittest.TestCase):
    def test_no_render_stage(self) -> None:
        names = [name for name, _ in verify.STAGES]
        self.assertEqual(names, ["watch", "verify", "guard"])

    def test_stage_scripts_exist(self) -> None:
        for _, command in verify.STAGES:
            self.assertTrue((ROOT / command[1]).is_file(), command[1])

    def test_guard_stage_is_no_render_mandates(self) -> None:
        guard = dict(verify.STAGES)["guard"]
        self.assertEqual(guard[1], "engineering-init/scripts/test_no_render_mandates.py")


class RunStageTests(unittest.TestCase):
    def test_pass(self) -> None:
        code = verify.run_stage(
            "ok", (sys.executable, "-c", "import sys; sys.exit(0)"), 30.0
        )
        self.assertEqual(code, 0)

    def test_failure_returncode_forwarded(self) -> None:
        code = verify.run_stage(
            "bad", (sys.executable, "-c", "import sys; sys.exit(3)"), 30.0
        )
        self.assertEqual(code, 3)

    def test_timeout_returns_124(self) -> None:
        code = verify.run_stage(
            "slow", (sys.executable, "-c", "import time; time.sleep(30)"), 0.5
        )
        self.assertEqual(code, verify.TIMEOUT_EXIT_CODE)

    def test_output_forwarded(self) -> None:
        code = verify.run_stage(
            "loud", (sys.executable, "-c", "print('hello-from-stage')"), 30.0
        )
        self.assertEqual(code, 0)

    def test_stage_timeouts_covers_stages(self) -> None:
        timeouts = {name: 1.0 for name, _ in verify.STAGES}
        self.assertEqual(sorted(timeouts), ["guard", "verify", "watch"])


if __name__ == "__main__":
    unittest.main()
