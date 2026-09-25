#!/usr/bin/env python3
"""Tests for the bounded verification runner and its stage list."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify

ROOT = Path(__file__).resolve().parents[2]


class StagesTests(unittest.TestCase):
    def test_no_render_stage(self) -> None:
        names = [name for name, _ in verify.STAGES]
        self.assertEqual(names, ["watch", "verify", "guard", "sessions", "spawn"])

    def test_stage_scripts_exist(self) -> None:
        for _, command in verify.STAGES:
            self.assertTrue((ROOT / command[1]).is_file(), command[1])

    def test_guard_stage_is_no_render_mandates(self) -> None:
        guard = dict(verify.STAGES)["guard"]
        self.assertEqual(guard[1], "engineering-init/scripts/test_no_render_mandates.py")


class VerifyRunnerTests(unittest.TestCase):
    def run_script(self, body: str, timeout: float = 2.0) -> tuple[int, str, str]:
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "stage.py"
            script.write_text(textwrap.dedent(body), encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = verify.run_stage(
                    "test", (sys.executable, str(script)), timeout
                )
        return returncode, stdout.getvalue(), stderr.getvalue()

    def test_success_forwards_output_and_reports_return_code(self) -> None:
        code, stdout, stderr = self.run_script(
            """
            import sys
            print('stage stdout')
            print('stage stderr', file=sys.stderr)
            """
        )
        self.assertEqual(code, 0)
        self.assertIn("stage stdout", stdout)
        self.assertIn("stage stderr", stderr)
        self.assertIn("[test] finished", stdout)
        self.assertIn("returncode=0", stdout)

    def test_failure_stops_with_stage_return_code(self) -> None:
        code, stdout, _ = self.run_script(
            """
            import sys
            print('failure detail', file=sys.stderr)
            raise SystemExit(7)
            """
        )
        self.assertEqual(code, 7)
        self.assertIn("failure detail", _)
        self.assertIn("returncode=7", stdout)

    @unittest.skipUnless(os.name == "nt" or hasattr(os, "killpg"), "process groups unavailable")
    def test_timeout_returns_bounded_timeout_code_and_terminates_child(self) -> None:
        code, stdout, stderr = self.run_script(
            """
            import subprocess
            import sys
            import time
            subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
            print('before timeout', flush=True)
            time.sleep(30)
            """,
            timeout=0.2,
        )
        self.assertEqual(code, verify.TIMEOUT_EXIT_CODE)
        self.assertIn("before timeout", stdout)
        self.assertIn("timeout", stdout)
        self.assertIn("returncode=124", stdout)
        self.assertEqual(stderr, "")


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
        self.assertEqual(
            sorted(timeouts), ["guard", "sessions", "spawn", "verify", "watch"]
        )


if __name__ == "__main__":
    unittest.main()
