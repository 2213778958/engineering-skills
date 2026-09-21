"""Tests for secure department GitHub credential binding."""
from __future__ import annotations
import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
MODULE_PATH = Path(__file__).with_name("spawn.py")
SPEC = importlib.util.spec_from_file_location("spawn", MODULE_PATH)
assert SPEC and SPEC.loader
spawn = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = spawn
SPEC.loader.exec_module(spawn)
class GitHubBindingTests(unittest.TestCase):
    """Exercise mapping, rejection, redaction, and isolation behavior."""
    def test_binding_maps_registered_source_to_consumer(self) -> None:
        binding = spawn.github_binding("GITHUB_PERSONAL_ACCESS_TOKEN", "session-key")
        self.assertEqual(
            binding,
            {
                "GH_TOKEN": {
                    "kind": "LookupSecret",
                    "url": (
                        "http://localhost:8000/api/settings/secrets/"
                        "GITHUB_PERSONAL_ACCESS_TOKEN"
                    ),
                    "headers": {"X-Session-API-Key": "session-key"},
                    "description": "GitHub token for an authorized department",
                }
            },
        )
    def test_none_and_invalid_source_fail_closed(self) -> None:
        for source in ("none", "", "TOKEN/../../other"):
            with self.subTest(source=source), self.assertRaises(SystemExit):
                spawn.github_binding(source, "session-key")
    def test_probe_rejects_authentication_and_unavailable_source(self) -> None:
        for code, message in ((401, "authentication failed"), (404, "unavailable")):
            error = spawn.HTTPError("url", code, "error", {}, None)
            with self.subTest(code=code), patch.object(
                spawn, "urlopen", side_effect=error
            ), self.assertRaisesRegex(SystemExit, message):
                spawn.probe_secret_source(
                    "GITHUB_PERSONAL_ACCESS_TOKEN", "session-key"
                )
    def test_create_rejection_does_not_disclose_response_or_credentials(self) -> None:
        error = spawn.HTTPError(
            "url", 422, "error", {}, io.BytesIO(b"server echoed secret material")
        )
        with patch.object(spawn, "urlopen", side_effect=error), self.assertRaises(
            SystemExit
        ) as caught:
            spawn.api(
                "POST",
                "/api/conversations",
                {"secrets": spawn.github_binding("SOURCE_TOKEN", "session-key")},
                redact_error=True,
            )
        text = str(caught.exception)
        self.assertNotIn("server echoed secret material", text)
        self.assertNotIn("session-key", text)
        self.assertNotIn("SOURCE_TOKEN", text)
    def test_create_network_error_is_redacted(self) -> None:
        error = spawn.URLError("server echoed secret material")
        with patch.object(spawn, "urlopen", side_effect=error), self.assertRaises(
            SystemExit
        ) as caught:
            spawn.api(
                "POST",
                "/api/conversations",
                {"secrets": spawn.github_binding("SOURCE_TOKEN", "session-key")},
                redact_error=True,
            )
        text = str(caught.exception)
        self.assertNotIn("server echoed secret material", text)
        self.assertNotIn("session-key", text)
        self.assertNotIn("SOURCE_TOKEN", text)
    def test_unbound_creation_isolated_from_department_secret(self) -> None:
        body = spawn.conversation_body(
            child_id="child",
            profile_id="profile",
            working_dir="workspace",
            prompt="employee-safe prompt",
            tags={"clientsource": "agentcanvas"},
            max_iterations=10,
            parent_id="parent",
        )
        self.assertNotIn("secrets", body)
        self.assertNotIn("GH_TOKEN", json.dumps(body))
    def test_bound_prompt_requires_redacted_preflight_and_receipt_preservation(self) -> None:
        prompt = spawn.bound_department_prompt("original task")
        self.assertIn("$env:GH_TOKEN", prompt)
        self.assertIn("gh auth status", prompt)
        self.assertIn("notify planning", prompt)
        self.assertIn("preserve completed receipts", prompt)
        self.assertNotIn("GITHUB_PERSONAL_ACCESS_TOKEN", prompt)
    def test_status_output_is_non_secret(self) -> None:
        status = spawn.binding_status(True)
        output = io.StringIO()
        with redirect_stdout(output):
            print(json.dumps(status))
        self.assertEqual(status, {"consumer": "GH_TOKEN", "status": "bound"})
        self.assertNotIn("session-key", output.getvalue())
        self.assertNotIn("GITHUB_PERSONAL_ACCESS_TOKEN", output.getvalue())
if __name__ == "__main__":
    unittest.main()
