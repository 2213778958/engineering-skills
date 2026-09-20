from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spawn = load("spawn")
github_command = load("github_command")


class CredentialTests(unittest.TestCase):
    def fake_gh(self, directory: Path) -> Path:
        path = directory / "gh.cmd"
        path.write_text(
            "@echo off\r\n"
            "if \"%GH_TOKEN%\"==\"expired\" (echo expired %GH_TOKEN% 1>&2 & exit /b 1)\r\n"
            "if \"%GH_TOKEN%\"==\"\" exit /b 1\r\n"
            "echo command-ok\r\n",
            encoding="utf-8",
        )
        return path

    def test_explicit_reference_injects_key_absent_at_startup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            gh = self.fake_gh(Path(raw))
            self.assertNotIn("GH_TOKEN", os.environ)
            self.assertEqual(
                github_command.run_github_command(
                    "PROCESS_REGISTERED_GITHUB_KEY",
                    "available-on-reference",
                    [str(gh), "api", "user"],
                ),
                0,
            )

    def test_cli_absent_at_startup_succeeds_on_explicit_reference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            gh = self.fake_gh(Path(raw))
            env = os.environ.copy()
            env.pop("GH_TOKEN", None)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "github_command.py"),
                    "--key-name",
                    "REGISTERED_KEY",
                    "--",
                    str(gh),
                    "api",
                    "user",
                ],
                input="injected-only-now\n",
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("command-ok", result.stdout)
        self.assertNotIn("injected-only-now", result.stdout + result.stderr)

    def test_none_and_unavailable_fail_with_class_and_name(self) -> None:
        with self.assertRaisesRegex(SystemExit, "credential none"):
            github_command.run_github_command("none", "", ["gh", "api", "user"])
        with self.assertRaisesRegex(SystemExit, "credential unavailable: CUSTOM_KEY"):
            github_command.run_github_command("CUSTOM_KEY", "", ["gh", "api", "user"])

    def test_expired_value_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            gh = self.fake_gh(Path(raw))
            os.environ["EXPIRED_KEY"] = "expired"
            try:
                with self.assertRaises(SystemExit) as caught:
                    github_command.run_github_command("EXPIRED_KEY", "expired", [str(gh), "api", "user"])
            finally:
                os.environ.pop("EXPIRED_KEY", None)
        message = str(caught.exception)
        self.assertIn("authentication-failed: EXPIRED_KEY", message)
        self.assertIn("[REDACTED]", message)
        self.assertNotIn("expired expired", message)


class IdentityTests(unittest.TestCase):
    def child(self, **overrides):
        child = {
            "id": "child-1",
            "parent_conversation_id": "parent-1",
            "execution_status": "finished",
            "workspace": {"working_dir": "C:/repo"},
            "tags": {
                "clientsource": "agentcanvas",
                "layer": "department",
                "dispatch_id": "dispatch-1",
                "department": "delivery",
                "ticket": "#24",
            },
        }
        child.update(overrides)
        return child

    def report(self, **overrides):
        fields = {
            "dispatch-id": "dispatch-1",
            "child-conversation-id": "child-1",
            "department": "delivery",
            "ticket": "#24",
        }
        fields.update(overrides)
        return "engineering:report\n" + "\n".join(f"{key}: {value}" for key, value in fields.items())

    def test_exact_report_correlation(self) -> None:
        self.assertEqual(spawn.validate_report(self.report(), self.child()), "exact")

    def test_mismatch_and_partial_legacy_are_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "identity mismatch"):
            spawn.validate_report(self.report(ticket="#23"), self.child())
        with self.assertRaisesRegex(SystemExit, "identity missing"):
            spawn.validate_report("engineering:report\ndepartment: delivery", self.child(), True)

    def test_legacy_requires_explicit_compatibility(self) -> None:
        legacy = "engineering:report\nhop: done"
        with self.assertRaisesRegex(SystemExit, "identity missing"):
            spawn.validate_report(legacy, self.child())
        self.assertEqual(spawn.validate_report(legacy, self.child(), True), "legacy-unverified")

    def test_resume_accepts_direct_department_child(self) -> None:
        parent = {"id": "parent-1", "workspace": {"working_dir": "C:/repo"}}
        self.assertEqual(
            spawn.validate_resume(parent, self.child(), "parent-1", "child-1"), "finished"
        )

    def test_resume_rejects_relationship_workspace_tag_layer_and_states(self) -> None:
        parent = {"id": "parent-1", "workspace": {"working_dir": "C:/repo"}}
        cases = [
            self.child(id="arbitrary-id"),
            self.child(parent_conversation_id="other"),
            self.child(workspace={"working_dir": "C:/other"}),
            self.child(tags={}),
            self.child(tags={**self.child()["tags"], "layer": "employee"}),
            self.child(tags={**self.child()["tags"], "department": "planning"}),
            self.child(execution_status="running"),
            self.child(execution_status="starting"),
        ]
        for child in cases:
            with self.subTest(child=child), self.assertRaises(SystemExit):
                spawn.validate_resume(parent, child, "parent-1", "child-1")

    def test_resume_rejects_wrong_direction(self) -> None:
        parent = {
            "id": "parent-1",
            "parent_conversation_id": "grandparent",
            "workspace": {"working_dir": "C:/repo"},
        }
        with self.assertRaisesRegex(SystemExit, "invalid direction"):
            spawn.validate_resume(parent, self.child(), "parent-1", "child-1")


if __name__ == "__main__":
    unittest.main()
