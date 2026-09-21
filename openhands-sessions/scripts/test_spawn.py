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

    def test_dispatch_post_timeout_is_300_seconds(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('"POST",\n        "/api/conversations",\n        body,\n        timeout=300,', source)

    def test_duplicate_active_dispatch_is_rejected(self) -> None:
        with patch.object(
            spawn,
            "search_items",
            return_value=[
                {
                    "id": "existing",
                    "parent_conversation_id": "parent",
                    "status": "running",
                    "tags": {"department": "delivery"},
                }
            ],
        ), self.assertRaisesRegex(SystemExit, "existing"):
            spawn.refuse_duplicate_dispatch(
                "parent", {"department": "delivery"}
            )

    def test_duplicate_dispatch_force_is_allowed(self) -> None:
        with patch.object(spawn, "search_items") as search:
            spawn.refuse_duplicate_dispatch(
                "parent", {"department": "delivery"}, force=True
            )
        search.assert_not_called()

    def test_duplicate_guard_ignores_other_parent_department_and_terminal(self) -> None:
        with patch.object(
            spawn,
            "search_items",
            return_value=[
                {
                    "id": "other-parent",
                    "parent_conversation_id": "other",
                    "status": "running",
                    "tags": {"department": "delivery"},
                },
                {
                    "id": "other-department",
                    "parent_conversation_id": "parent",
                    "status": "running",
                    "tags": {"department": "acceptance"},
                },
                {
                    "id": "finished",
                    "parent_conversation_id": "parent",
                    "status": "finished",
                    "tags": {"department": "delivery"},
                },
            ],
        ):
            spawn.refuse_duplicate_dispatch("parent", {"department": "delivery"})

    def test_search_items_fails_closed_on_uncertain_payload(self) -> None:
        for payload in ({}, {"items": ["not-an-item"]}):
            with self.subTest(payload=payload), patch.object(
                spawn, "api", return_value=payload
            ), self.assertRaisesRegex(SystemExit, "invalid"):
                spawn.search_items()

    def test_search_items_reads_all_pages(self) -> None:
        pages = [
            {"items": [{"id": "first"}], "has_more": True},
            {"items": [{"id": "second"}], "has_more": False},
        ]
        with patch.object(spawn, "api", side_effect=pages) as api:
            self.assertEqual(
                [item["id"] for item in spawn.search_items()], ["first", "second"]
            )
        self.assertIn("offset=1", api.call_args_list[1].args[1])

    def test_search_items_follows_cursor_pages(self) -> None:
        with patch.object(
            spawn,
            "api",
            side_effect=[
                {"items": [{"id": "first"}], "next_cursor": "next"},
                {"items": [{"id": "second"}]},
            ],
        ) as api:
            self.assertEqual(
                [item["id"] for item in spawn.search_items()], ["first", "second"]
            )
        self.assertIn("cursor=next", api.call_args_list[1].args[1])

    def test_search_items_rejects_repeated_cursor(self) -> None:
        with patch.object(
            spawn, "api", return_value={"items": [], "next_cursor": "same"}
        ), self.assertRaisesRegex(SystemExit, "next cursor"):
            spawn.search_items()

    def test_search_items_rejects_cursor_cycle(self) -> None:
        with patch.object(
            spawn,
            "api",
            side_effect=[
                {"items": [], "next_cursor": "a"},
                {"items": [], "next_cursor": "b"},
                {"items": [], "next_cursor": "a"},
            ],
        ) as api, self.assertRaisesRegex(SystemExit, "next cursor"):
            spawn.search_items()
        self.assertEqual(api.call_count, 3)

    def test_dispatch_child_id_is_stable_reservation_key(self) -> None:
        first = spawn.dispatch_child_id("parent", "delivery")
        self.assertEqual(first, spawn.dispatch_child_id("parent", "delivery"))
        self.assertNotEqual(first, spawn.dispatch_child_id("parent", "acceptance"))
        self.assertRegex(first, r"^[0-9a-f-]{36}$")


    def test_skill_documents_soft_timeout_and_duplicate_contract(self) -> None:
        skill = (MODULE_PATH.parent.parent / "SKILL.md").read_text(encoding="utf-8")
        for text in (
            "terminal timeout to at least 300 seconds",
            "terminal soft timeout (`exit=-1`) is not a dispatch failure",
            "receipt JSON containing `conversation_id` or `id` as success",
            "GET the child status before retrying",
            "never retry an active or unknown child",
            "use `--force` only when the duplicate is intentional",
        ):
            with self.subTest(text=text):
                self.assertIn(text, skill)


if __name__ == "__main__":
    unittest.main()
