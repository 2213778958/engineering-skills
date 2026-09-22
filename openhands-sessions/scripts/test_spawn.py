"""Tests for secure department GitHub credential binding.

Fixture justification: patching ``spawn.api`` / ``spawn.search_items`` /
``spawn.urlopen`` follows the established in-repo fixture pattern so tests
drive real adapter code paths deterministically without network access.
The dispatch ledger is redirected to a temp directory via the
``OPENHANDS_DISPATCH_LEDGER_DIR`` override so tests never touch the real
user ledger. One timeout test uses a local controlled HTTP fixture on
127.0.0.1 with an ephemeral port because timeout classification is a
socket-level behavior that cannot be observed through a patched ``api``.
"""
from __future__ import annotations
import argparse
import importlib.util
import io
import json
import os
import re
import shutil
import socketserver
import sys
import tempfile
import threading
import unittest
import urllib.request
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

    def test_conversation_creation_post_timeout_is_180_seconds(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            '"POST",\n        "/api/conversations",\n        body,\n        timeout=180,',
            source,
        )

    def test_dispatch_get_child_uses_180_second_timeout(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        pattern = re.compile(
            r"checked = get_conversation\(cid, timeout=180\)\n.{0,120}?if checked is None",
            re.DOTALL,
        )
        self.assertIsNotNone(pattern.search(source))

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

    def test_search_items_follows_page_id_pages_without_offset_progression(self) -> None:
        with patch.object(
            spawn,
            "api",
            side_effect=[
                {"items": [{"id": "first"}], "next_page_id": "page-2"},
                {"items": [{"id": "second"}]},
            ],
        ) as api:
            self.assertEqual(
                [item["id"] for item in spawn.search_items()], ["first", "second"]
            )
        self.assertIn("page_id=page-2", api.call_args_list[1].args[1])
        self.assertIn("offset=0", api.call_args_list[1].args[1])

    def test_search_items_rejects_repeated_page_id(self) -> None:
        with patch.object(
            spawn,
            "api",
            side_effect=[
                {"items": [{"id": "first"}], "next_page_id": "same"},
                {"items": [{"id": "second"}], "next_page_id": "same"},
            ],
        ), self.assertRaisesRegex(SystemExit, "next page id"):
            spawn.search_items()

    def test_search_items_rejects_repeated_page(self) -> None:
        page = {"items": [{"id": "same"}], "has_more": True}
        with patch.object(spawn, "api", side_effect=[page, page]), self.assertRaisesRegex(
            SystemExit, "repeated page"
        ):
            spawn.search_items()


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

    def test_dispatch_request_identity_scopes_ticket_and_request(self) -> None:
        """Updated for #41: the old parent+department-only key aliased requests."""
        base = ("parent", "delivery", "#41", "req-1")
        first = spawn.dispatch_request_child_id(*base)
        self.assertEqual(first, spawn.dispatch_request_child_id(*base))
        self.assertNotEqual(
            first, spawn.dispatch_request_child_id("parent", "delivery", "#42", "req-1")
        )
        self.assertNotEqual(
            first, spawn.dispatch_request_child_id("parent", "delivery", "#41", "req-2")
        )
        self.assertNotEqual(
            first, spawn.dispatch_request_child_id("parent", "acceptance", "#41", "req-1")
        )
        self.assertRegex(first, r"^[0-9a-f-]{36}$")
        self.assertEqual(
            spawn.request_identity(*base),
            "dispatch:parent:delivery:#41:req-1",
        )


    def test_skill_documents_soft_timeout_and_duplicate_contract(self) -> None:
        skill = (MODULE_PATH.parent.parent / "SKILL.md").read_text(encoding="utf-8")
        for text in (
            "terminal timeout to at least 200 seconds",
            "terminal soft timeout (`exit=-1`) is not a dispatch failure",
            "receipt JSON containing `conversation_id` or `id` as success",
            "GET the child status before retrying",
            "never retry an active or unknown child",
            "use `--force` only when the duplicate is intentional",
        ):
            with self.subTest(text=text):
                self.assertIn(text, skill)


PARENT = "11111111-1111-4111-8111-111111111111"
CHILD = "22222222-2222-4222-8222-222222222222"
OTHER = "33333333-3333-4333-8333-333333333333"
TARGET = "44444444-4444-4444-8444-444444444444"
PROFILE = "12345678-1234-5678-1234-567812345678"
REAL_URLOPEN = urllib.request.urlopen


def api_recorder(convs: dict, posts: list):
    """Drive real adapter code paths through a controlled in-memory backend."""

    def record(method, path, body=None, timeout=60, redact_error=False):
        if path.startswith("/api/conversations/search"):
            return {"items": []}
        if method == "POST" and path == "/api/conversations":
            posts.append(path)
            return dict(convs.get("__create__", {"id": CHILD, "conversation_id": ""}))
        if method == "POST" and (path.endswith("/events") or path.endswith("/run")):
            posts.append(path)
            return {}
        if method == "GET" and path.startswith("/api/conversations/"):
            cid = path.rsplit("/", 1)[-1]
            if cid in convs:
                return convs[cid]
            raise SystemExit(f"HTTP 404 GET {path}: not found")
        return {}

    return record


class LedgerIsolatedTestCase(unittest.TestCase):
    """Redirect the dispatch ledger and workspace to temp dirs per test."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="spawn41-")
        self.prev_ledger_dir = os.environ.get("OPENHANDS_DISPATCH_LEDGER_DIR")
        os.environ["OPENHANDS_DISPATCH_LEDGER_DIR"] = os.path.join(self.tmp, "ledger")
        self.wd = os.path.join(self.tmp, "proj")
        os.makedirs(self.wd, exist_ok=True)
        self.posts: list = []

    def tearDown(self) -> None:
        if self.prev_ledger_dir is None:
            os.environ.pop("OPENHANDS_DISPATCH_LEDGER_DIR", None)
        else:
            os.environ["OPENHANDS_DISPATCH_LEDGER_DIR"] = self.prev_ledger_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def prompt_file(self, name: str, content: str) -> str:
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def parent_conv(self, **over):
        conv = {
            "id": PARENT,
            "workspace": {"kind": "LocalWorkspace", "working_dir": self.wd},
            "tags": {"clientsource": "agentcanvas"},
            "parent_conversation_id": None,
        }
        conv.update(over)
        return conv

    def child_conv(self, cid: str = CHILD, status: str = "running", **over):
        conv = {
            "id": cid,
            "conversation_id": "",
            "workspace": {"kind": "LocalWorkspace", "working_dir": self.wd},
            "tags": {"clientsource": "agentcanvas", "department": "delivery"},
            "parent_conversation_id": PARENT,
            "status": status,
        }
        conv.update(over)
        return conv

    def dispatch_args(self, **over):
        base = dict(
            mode="dispatch",
            this_id="",
            profile_id=PROFILE,
            department="delivery",
            github_token_secret="",
            prompt_file=self.prompt_file(
                "task.txt", "continue ticket #41 delivery work"
            ),
            max_iterations=500,
            poll_sec=0,
            timeout_sec=5400,
            force=False,
            ticket="#41",
            request_id="req-aaa1",
            target_id="",
            related_request_id="",
        )
        base.update(over)
        return argparse.Namespace(**base)

    def resume_args(self, **over):
        base = dict(
            mode="resume",
            this_id="",
            profile_id="",
            department="",
            github_token_secret="",
            prompt_file=self.prompt_file("resume.txt", "resume: continue hop 2"),
            max_iterations=500,
            poll_sec=0,
            timeout_sec=5400,
            force=False,
            ticket="#41",
            request_id="req-res1",
            target_id=TARGET,
            related_request_id="",
        )
        base.update(over)
        return argparse.Namespace(**base)

    def bind_target(self, status: str = "accepted", ticket: str = "#41") -> None:
        spawn.record_ledger(
            PARENT,
            "req-disp0",
            spawn.ledger_entry(
                operation="dispatch",
                request_id="req-disp0",
                ticket=ticket,
                department="delivery",
                parent_id=PARENT,
                status=status,
                evidence="prior accepted dispatch",
                child_id=TARGET,
                prompt_sha256=spawn.prompt_digest("prior"),
                profile_id=PROFILE,
                working_dir=self.wd,
            ),
        )

    def output_of(self, fn, *args) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            fn(*args)
        return out.getvalue()


class ProfileIdentityTests(LedgerIsolatedTestCase):
    """--profile-id is the Agent Canvas profile UUID, never a display name."""

    def test_name_shaped_profile_id_is_rejected_with_catalog_hint(self) -> None:
        with self.assertRaisesRegex(SystemExit, "agent-profiles"):
            spawn.validate_profile_id("deepseek-max")
        with self.assertRaisesRegex(SystemExit, "UUID"):
            spawn.validate_profile_id("DeepSeek Max (high)")

    def test_uuid_profile_id_is_accepted(self) -> None:
        self.assertEqual(spawn.validate_profile_id(PROFILE), PROFILE)
        self.assertEqual(
            spawn.validate_profile_id(PROFILE.upper()), PROFILE.upper()
        )

    def test_name_profile_fails_closed_before_any_post(self) -> None:
        with patch.object(
            spawn,
            "api",
            side_effect=api_recorder({}, self.posts),
        ), self.assertRaisesRegex(SystemExit, "agent-profiles"):
            spawn.run_dispatch(
                self.dispatch_args(profile_id="deepseek-max"),
                self.parent_conv(),
                PARENT,
            )
        self.assertEqual(self.posts, [])

    def test_ticket_and_request_id_are_validated(self) -> None:
        with self.assertRaisesRegex(SystemExit, "--ticket"):
            spawn.normalize_ticket("41")
        with self.assertRaisesRegex(SystemExit, "--request-id"):
            spawn.normalize_request_id("ab")


class DispatchLedgerTests(LedgerIsolatedTestCase):
    """Request-scoped dispatch identity, ledger reconciliation, fail-closed."""

    def test_same_request_retry_reconciles_without_second_post(self) -> None:
        recorder = api_recorder({CHILD: self.child_conv()}, self.posts)
        with patch.object(spawn, "api", side_effect=recorder):
            self.output_of(
                spawn.run_dispatch, self.dispatch_args(), self.parent_conv()
            )
            self.assertEqual(self.posts, ["/api/conversations"])
            receipt = self.output_of(
                spawn.run_dispatch, self.dispatch_args(), self.parent_conv()
            )
        self.assertEqual(self.posts, ["/api/conversations"])
        self.assertIn('"reconciled": true', receipt)
        entry = spawn.load_ledger(PARENT)["req-aaa1"]
        self.assertEqual(entry["status"], "accepted")
        self.assertEqual(entry["ticket"], "#41")
        self.assertEqual(entry["department"], "delivery")

    def test_changed_payload_same_request_fails_closed_before_post(self) -> None:
        recorder = api_recorder({CHILD: self.child_conv()}, self.posts)
        with patch.object(spawn, "api", side_effect=recorder):
            self.output_of(
                spawn.run_dispatch, self.dispatch_args(), self.parent_conv()
            )
            with self.assertRaisesRegex(SystemExit, "collision"):
                spawn.run_dispatch(
                    self.dispatch_args(
                        prompt_file=self.prompt_file("other.txt", "different task")
                    ),
                    self.parent_conv(),
                    PARENT,
                )
        self.assertEqual(self.posts, ["/api/conversations"])

    def test_dispatch_timeout_records_unknown_then_replay_reconciles(self) -> None:
        with patch.object(
            spawn, "api", side_effect=TimeoutError("connection timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_dispatch, self.dispatch_args(), self.parent_conv()
            )
        entry = spawn.load_ledger(PARENT)["req-aaa1"]
        self.assertEqual(entry["status"], "unknown")
        self.assertEqual(self.posts, [])
        retry_child = spawn.dispatch_request_child_id(
            PARENT, "delivery", "#41", "req-aaa1"
        )
        recorder = api_recorder(
            {retry_child: self.child_conv(cid=retry_child, status="running")},
            self.posts,
        )
        with patch.object(spawn, "api", side_effect=recorder):
            receipt = self.output_of(
                spawn.run_dispatch, self.dispatch_args(), self.parent_conv()
            )
        self.assertEqual(self.posts, [])
        self.assertIn('"receipt": "accepted"', receipt)
        self.assertIn('"reconciled": true', receipt)

    def test_rejected_dispatch_is_recorded_and_not_retried(self) -> None:
        with patch.object(
            spawn,
            "api",
            side_effect=SystemExit("HTTP 422 POST /api/conversations: bad request"),
        ), self.assertRaisesRegex(SystemExit, "HTTP 422"):
            self.output_of(
                spawn.run_dispatch, self.dispatch_args(), self.parent_conv()
            )
        self.assertEqual(spawn.load_ledger(PARENT)["req-aaa1"]["status"], "rejected")
        with patch.object(
            spawn, "api", side_effect=api_recorder({}, self.posts)
        ), self.assertRaisesRegex(SystemExit, "previously rejected"):
            spawn.run_dispatch(self.dispatch_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_active_ledger_dispatch_blocks_second_request_until_forced(self) -> None:
        self.bind_target(status="accepted")
        convs = {
            TARGET: self.child_conv(cid=TARGET, status="running"),
            CHILD: self.child_conv(cid=CHILD, status="running"),
        }
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "already exists"):
                spawn.run_dispatch(
                    self.dispatch_args(request_id="req-new9"),
                    self.parent_conv(),
                    PARENT,
                )
            self.assertEqual(self.posts, [])
            self.output_of(
                spawn.run_dispatch,
                self.dispatch_args(request_id="req-new9", force=True),
                self.parent_conv(),
            )
        self.assertEqual(self.posts, ["/api/conversations"])


class ResumeTests(LedgerIsolatedTestCase):
    """Explicit resume of the exact original direct-child department target."""

    def setUp(self) -> None:
        super().setUp()
        self.bind_target()

    def test_resume_finished_child_posts_event_exact_target_without_create(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            out = self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
        self.assertEqual(self.posts, [f"/api/conversations/{TARGET}/events"])
        self.assertIn('"receipt": "accepted"', out)
        self.assertIn('"operation": "resume"', out)
        self.assertIn(TARGET, out)

    def test_resume_rejects_missing_target(self) -> None:
        with patch.object(spawn, "api", side_effect=api_recorder({}, self.posts)):
            with self.assertRaisesRegex(SystemExit, "does not exist"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_non_direct_child(self) -> None:
        convs = {
            TARGET: self.child_conv(
                cid=TARGET, status="finished", parent_conversation_id=OTHER
            )
        }
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "direct child"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_wrong_department(self) -> None:
        convs = {
            TARGET: self.child_conv(
                cid=TARGET, status="finished", tags={"clientsource": "agentcanvas", "department": "acceptance"}
            )
        }
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "department"):
                spawn.run_resume(
                    self.resume_args(department="delivery"),
                    self.parent_conv(),
                    PARENT,
                )
        self.assertEqual(self.posts, [])

    def test_resume_rejects_workspace_mismatch(self) -> None:
        convs = {
            TARGET: self.child_conv(
                cid=TARGET,
                status="finished",
                workspace={"kind": "LocalWorkspace", "working_dir": os.path.join(self.tmp, "elsewhere")},
            )
        }
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "workspace"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_missing_clientsource_tag(self) -> None:
        convs = {
            TARGET: self.child_conv(
                cid=TARGET, status="finished", tags={"department": "delivery"}
            )
        }
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "clientsource"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_active_target_without_concurrent_run(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="running")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "active"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_stopped_target_without_silent_success(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="stopped")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "stopped"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_child_unbound_in_ledger(self) -> None:
        ledger = spawn.load_ledger(PARENT)
        ledger.pop("req-disp0")
        spawn.save_ledger(PARENT, ledger)
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "authorized department child"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_ticket_mismatch_is_rejected(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "ticket"):
                spawn.run_resume(
                    self.resume_args(ticket="#42"), self.parent_conv(), PARENT
                )
        self.assertEqual(self.posts, [])

    def test_resume_error_target_allows_single_bounded_attempt(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="error")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
            self.assertEqual(self.posts, [f"/api/conversations/{TARGET}/events"])
            replay = self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv(), PARENT
            )
            self.assertIn('"reconciled": true', replay)
        self.assertEqual(self.posts.count(f"/api/conversations/{TARGET}/events"), 1)

    def test_resume_timeout_yields_unknown_then_reconciles_running(self) -> None:
        with patch.object(
            spawn, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
        entry = spawn.load_ledger(PARENT)["req-res1"]
        self.assertEqual(entry["status"], "unknown")
        self.assertEqual(entry["target_id"], TARGET)
        convs = {TARGET: self.child_conv(cid=TARGET, status="running")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            receipt = self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
        self.assertEqual(self.posts, [])
        self.assertIn('"receipt": "accepted"', receipt)
        self.assertIn('"reconciled": true', receipt)

    def test_resume_unknown_still_finished_resends_once_then_unknown(self) -> None:
        with patch.object(
            spawn, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
            self.assertEqual(
                self.posts, [f"/api/conversations/{TARGET}/events"]
            )
            replay = self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
            self.assertIn('"reconciled": true', replay)
        self.assertEqual(
            self.posts.count(f"/api/conversations/{TARGET}/events"), 1
        )

    def test_resume_socket_timeout_yields_unknown_receipt(self) -> None:
        class StallHandler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                import time

                time.sleep(5)

        server = socketserver.TCPServer(("127.0.0.1", 0), StallHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = spawn.BASE
        try:
            spawn.BASE = f"http://127.0.0.1:{port}"

            def slow_urlopen(req, timeout=None):
                return REAL_URLOPEN(req, timeout=1)

            with patch.object(spawn, "session_key", return_value="test-key"), patch.object(
                spawn, "urlopen", slow_urlopen
            ), self.assertRaises((SystemExit, TimeoutError)):
                self.output_of(
                    spawn.run_resume, self.resume_args(), self.parent_conv()
                )
        finally:
            spawn.BASE = base
            server.shutdown()
            server.server_close()
        entry = spawn.load_ledger(PARENT).get("req-res1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["status"], "unknown")
        self.assertIn("target", entry["evidence"])


class NotifyIdentityTests(LedgerIsolatedTestCase):
    """Notify direction, related-request round-trip match, replay reconcile."""

    def setUp(self) -> None:
        super().setUp()
        self.bind_target()
        ledger = spawn.load_ledger(PARENT)
        entry = ledger.pop("req-disp0")
        entry["request_id"] = "req-not1"
        entry["child_id"] = CHILD
        ledger["req-not1"] = entry
        spawn.save_ledger(PARENT, ledger)

    def child_window(self) -> dict:
        return {
            "id": CHILD,
            "workspace": {"kind": "LocalWorkspace", "working_dir": self.wd},
            "tags": {"clientsource": "agentcanvas", "department": "delivery"},
            "parent_conversation_id": PARENT,
        }

    def notify_args(self, **over):
        base = dict(
            mode="notify",
            this_id="",
            profile_id="",
            department="",
            github_token_secret="",
            prompt_file=self.prompt_file(
                "report.txt",
                "engineering:report\ndepartment: delivery\nticket: #41\nhop: done\nrequest: req-not1\n",
            ),
            max_iterations=500,
            poll_sec=0,
            timeout_sec=5400,
            force=False,
            ticket="",
            request_id="req-report1",
            target_id="",
            related_request_id="",
        )
        base.update(over)
        return argparse.Namespace(**base)

    def test_related_request_match_posts_to_parent_and_accepts(self) -> None:
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            out = self.output_of(
                spawn.run_notify,
                self.notify_args(related_request_id="req-not1"),
                self.child_window(),
                CHILD,
            )
        self.assertIn(f"/api/conversations/{PARENT}/events", self.posts)
        self.assertIn('"receipt": "accepted"', out)

    def test_related_request_mismatch_rejected_without_post(self) -> None:
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "stale"):
                spawn.run_notify(
                    self.notify_args(related_request_id="req-other"),
                    self.child_window(),
                    CHILD,
                )
        self.assertEqual(self.posts, [])
        self.assertNotIn("req-report1", spawn.load_ledger(PARENT))

    def test_identical_replay_reconciles_without_second_post(self) -> None:
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            self.output_of(spawn.run_notify, self.notify_args(), self.child_window(), CHILD)
            receipt = self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        self.assertEqual(
            self.posts.count(f"/api/conversations/{PARENT}/events"), 1
        )
        self.assertIn('"reconciled": true', receipt)

    def test_changed_text_same_request_rejected(self) -> None:
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)):
            self.output_of(spawn.run_notify, self.notify_args(), self.child_window(), CHILD)
            with self.assertRaisesRegex(SystemExit, "collision"):
                spawn.run_notify(
                    self.notify_args(
                        prompt_file=self.prompt_file(
                            "report2.txt",
                            "engineering:report\ndepartment: delivery\nticket: #41\nrequest: req-not1\nhop: blocked\n",
                        )
                    ),
                    self.child_window(),
                    CHILD,
                )
        self.assertEqual(
            self.posts.count(f"/api/conversations/{PARENT}/events"), 1
        )

    def test_planning_direction_is_refused(self) -> None:
        with patch.object(spawn, "api", side_effect=api_recorder({}, self.posts)):
            with self.assertRaisesRegex(SystemExit, "Planning must not notify"):
                spawn.run_notify(
                    self.notify_args(), self.parent_conv(), PARENT
                )
        self.assertEqual(self.posts, [])


class CompletionSemanticsTests(LedgerIsolatedTestCase):
    """accepted receipt is emitted and the run returns when polling is off."""

    def test_accepted_dispatch_returns_immediately_with_receipt(self) -> None:
        recorder = api_recorder({CHILD: self.child_conv()}, self.posts)
        with patch.object(spawn, "api", side_effect=recorder), patch.object(
            spawn.time, "sleep"
        ) as sleeper:
            out = self.output_of(
                spawn.run_dispatch, self.dispatch_args(poll_sec=0), self.parent_conv()
            )
        self.assertEqual(self.posts, ["/api/conversations"])
        self.assertIn('"receipt": "accepted"', out)
        self.assertIn('"operation": "dispatch"', out)
        sleeper.assert_not_called()

    def test_accepted_resume_returns_immediately_with_receipt(self) -> None:
        self.bind_target()
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        with patch.object(spawn, "api", side_effect=api_recorder(convs, self.posts)), patch.object(
            spawn.time, "sleep"
        ) as sleeper:
            out = self.output_of(
                spawn.run_resume,
                self.resume_args(poll_sec=0),
                self.parent_conv(),
            )
        self.assertEqual(self.posts, [f"/api/conversations/{TARGET}/events"])
        self.assertIn('"receipt": "accepted"', out)
        sleeper.assert_not_called()


class ReceiptShapeTests(LedgerIsolatedTestCase):
    """Receipts carry the required structured fields, never credentials."""

    def test_receipt_fields_present(self) -> None:
        receipt = spawn.make_receipt(
            "accepted",
            operation="dispatch",
            request_id="req-1",
            ticket="#41",
            department="delivery",
            parent_id=PARENT,
            target_id=CHILD,
            evidence="POST accepted",
        )
        for key in (
            "receipt",
            "operation",
            "request_id",
            "ticket",
            "department",
            "parent_id",
            "target_id",
            "evidence",
            "next_action",
        ):
            self.assertIn(key, receipt)
        self.assertNotEqual(receipt["receipt"], "finished")

    def test_ledger_contains_no_secret_looking_values(self) -> None:
        self.bind_target()
        blob = json.dumps(spawn.load_ledger(PARENT))
        for banned in ("X-Session-API-Key", "api-key", "GH_TOKEN", "ghp_"):
            self.assertNotIn(banned, blob)

    def test_ledger_rejects_non_uuid_parent(self) -> None:
        with self.assertRaisesRegex(SystemExit, "UUID"):
            spawn.load_ledger("../../etc")


if __name__ == "__main__":
    unittest.main()
