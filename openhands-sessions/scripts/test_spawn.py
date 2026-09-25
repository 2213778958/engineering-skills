"""Tests for secure department GitHub credential binding.

Fixture justification: patching the transport and identity seams
(``transport.api`` / ``transport.urlopen`` / ``transport.session_key`` /
``identity.search_items``) follows the established in-repo fixture pattern so
tests drive real adapter code paths deterministically without network access.
The dispatch ledger is redirected to a temp directory via the
``OPENHANDS_DISPATCH_LEDGER_DIR`` override so tests never touch the real
user ledger. One timeout test uses a local controlled HTTP fixture on
127.0.0.1 with an ephemeral port because timeout classification is a
socket-level behavior that cannot be observed through a patched ``api``.
"""
from __future__ import annotations
import argparse
import http.client
import http.server
import importlib.util
import io
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable
from unittest.mock import patch
MODULE_PATH = Path(__file__).with_name("spawn.py")
SPEC = importlib.util.spec_from_file_location("spawn", MODULE_PATH)
assert SPEC and SPEC.loader
spawn = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = spawn
SPEC.loader.exec_module(spawn)
from canvas_sessions import dispatch, identity, ledger, resume, transport
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
            with self.subTest(code=code), patch.object(transport, "urlopen", side_effect=error
            ), self.assertRaisesRegex(SystemExit, message):
                spawn.probe_secret_source(
                    "GITHUB_PERSONAL_ACCESS_TOKEN", "session-key"
                )
    def test_create_rejection_does_not_disclose_response_or_credentials(self) -> None:
        error = spawn.HTTPError(
            "url", 422, "error", {}, io.BytesIO(b"server echoed secret material")
        )
        with patch.object(transport, "urlopen", side_effect=error), self.assertRaises(
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
        with patch.object(transport, "urlopen", side_effect=error), self.assertRaises(
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
        source = (MODULE_PATH.parent / "canvas_sessions" / "transport.py").read_text(
            encoding="utf-8"
        )
        pattern = re.compile(
            r"checked = get_conversation\(cid, timeout=180\)\n.{0,120}?if checked is None",
            re.DOTALL,
        )
        self.assertIsNotNone(pattern.search(source))

    def test_event_post_timeouts_use_module_constant(self) -> None:
        source = (MODULE_PATH.parent / "canvas_sessions" / "transport.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("EVENT_POST_TIMEOUT = 180", source)
        seam_dir = MODULE_PATH.parent / "canvas_sessions"
        negative = ""
        for seam in ("resume", "notify"):
            seam_source = (seam_dir / f"{seam}.py").read_text(encoding="utf-8")
            negative += seam_source
            with self.subTest(operation=seam):
                self.assertIn(
                    "timeout=transport.EVENT_POST_TIMEOUT,\n"
                    f'            operation="{seam}",',
                    seam_source,
                )
        self.assertNotIn("timeout=60,\n            operation=", negative)

    def test_duplicate_active_dispatch_is_rejected(self) -> None:
        with patch.object(identity, "search_items",
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
        with patch.object(identity, "search_items") as search:
            spawn.refuse_duplicate_dispatch(
                "parent", {"department": "delivery"}, force=True
            )
        search.assert_not_called()

    def test_duplicate_guard_ignores_other_parent_department_and_terminal(self) -> None:
        with patch.object(identity, "search_items",
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
            with self.subTest(payload=payload), patch.object(transport, "api", return_value=payload
            ), self.assertRaisesRegex(SystemExit, "invalid"):
                spawn.search_items()

    def test_search_items_reads_all_pages(self) -> None:
        pages = [
            {"items": [{"id": "first"}], "has_more": True},
            {"items": [{"id": "second"}], "has_more": False},
        ]
        with patch.object(transport, "api", side_effect=pages) as api:
            self.assertEqual(
                [item["id"] for item in spawn.search_items()], ["first", "second"]
            )
        self.assertIn("offset=1", api.call_args_list[1].args[1])

    def test_search_items_follows_cursor_pages(self) -> None:
        with patch.object(transport, "api",
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
        with patch.object(transport, "api",
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
        with patch.object(transport, "api",
            side_effect=[
                {"items": [{"id": "first"}], "next_page_id": "same"},
                {"items": [{"id": "second"}], "next_page_id": "same"},
            ],
        ), self.assertRaisesRegex(SystemExit, "next page id"):
            spawn.search_items()

    def test_search_items_rejects_repeated_page(self) -> None:
        page = {"items": [{"id": "same"}], "has_more": True}
        with patch.object(transport, "api", side_effect=[page, page]), self.assertRaisesRegex(
            SystemExit, "repeated page"
        ):
            spawn.search_items()


    def test_search_items_rejects_repeated_cursor(self) -> None:
        with patch.object(transport, "api", return_value={"items": [], "next_cursor": "same"}
        ), self.assertRaisesRegex(SystemExit, "next cursor"):
            spawn.search_items()

    def test_search_items_rejects_cursor_cycle(self) -> None:
        with patch.object(transport, "api",
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


def api_recorder(
    convs: dict,
    posts: list,
    events: dict | None = None,
    persist: Callable[[str, dict], object] | None = None,
):
    """Drive real adapter code paths through a controlled in-memory backend.

    Args:
        convs: Conversation lookup keyed by id.
        posts: Receives the POSTed paths.
        events: Optional seed of persisted events per conversation id, served
            by GET ``/api/conversations/{id}/events/search`` (#53: the
            conversation id lives before the ``/events`` segment even with
            the query string appended) as ``{"items": [...]}``. POSTed
            role-form events are appended to the store (#56: the real
            backend persists them verbatim under the user MessageEvent
            kind), so a post-POST delivery readback observes the landing.
        persist: Optional callable ``(cid, body) -> event | None`` overriding
            how a POSTed event is persisted (#56): the returned event is
            stored verbatim, and ``None`` models the event not persisting at
            all. Lets tests reproduce the #49 backend defect (POST accepted
            yet persisted with empty content) and sibling readback failures
            without touching production code.
    """
    store: dict[str, list] = {cid: list(seed) for cid, seed in (events or {}).items()}

    def record(method, path, body=None, timeout=60, redact_error=False):
        if path.startswith("/api/conversations/search"):
            return {"items": []}
        if method == "GET" and "/events" in path:
            scoped = path[len("/api/conversations/") :]
            cid = scoped.split("/events", 1)[0]
            return {"items": list(store.get(cid, []))}
        if method == "POST" and path == "/api/conversations":
            posts.append(path)
            requested = str((body or {}).get("conversation_id") or "")
            if requested:
                if requested in convs:
                    return dict(convs[requested])
                return {"id": requested, "conversation_id": ""}
            return dict(convs.get("__create__", {"id": CHILD, "conversation_id": ""}))
        if method == "POST" and path.endswith("/events"):
            posts.append(path)
            scoped = path[len("/api/conversations/") :]
            cid = scoped.split("/events", 1)[0]
            if persist is not None:
                event = persist(cid, body)
                if event is not None:
                    store.setdefault(cid, []).append(event)
            else:
                store.setdefault(cid, []).append(
                    {"kind": "MessageEvent", "source": "user", "llm_message": body}
                )
            return {}
        if method == "POST" and path.endswith("/run"):
            posts.append(path)
            return {}
        if method == "GET" and path.startswith("/api/conversations/"):
            cid = path.rsplit("/", 1)[-1]
            if cid in convs:
                return convs[cid]
            raise SystemExit(f"HTTP 404 GET {path}: not found")
        return {}

    return record


def body_capturing_recorder(convs: dict, posts: list, bodies: list, creates: list | None = None):
    """api_recorder that additionally captures POSTed JSON bodies.

    Args:
        convs: Conversation lookup keyed by id.
        posts: Receives the POSTed paths, same contract as api_recorder.
        bodies: Receives the JSON body dicts of event/run POSTs in order.
        creates: When given, additionally receives the JSON body dicts of
            conversation-create POSTs in order (identity-injection probe).
    """
    record = api_recorder(convs, posts)

    def capture(method, path, body=None, timeout=60, redact_error=False):
        if method == "POST" and (
            path.endswith("/events") or path.endswith("/run")
        ):
            bodies.append(body)
        if creates is not None and method == "POST" and path == "/api/conversations":
            creates.append(body)
        return record(method, path, body, timeout, redact_error)

    return capture


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

    def capture_output_of(self, fn, *args) -> tuple[str, str]:
        """Run ``fn`` capturing stdout; return (stdout, stderr) strings."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            fn(*args)
        return out.getvalue(), err.getvalue()


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
        with patch.object(transport, "api",
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
        # Issue #53: the created child id is derived from the request
        # identity, so the retry's reconciliation GET must find that exact
        # child (running) instead of a pre-baked unrelated fixture id.
        derived = spawn.dispatch_request_child_id(
            PARENT, "delivery", "#41", "req-aaa1"
        )
        recorder = api_recorder(
            {derived: self.child_conv(cid=derived)}, self.posts
        )
        with patch.object(transport, "api", side_effect=recorder):
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
        with patch.object(transport, "api", side_effect=recorder):
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
        with patch.object(transport, "api", side_effect=TimeoutError("connection timed out")
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
        with patch.object(transport, "api", side_effect=recorder):
            receipt = self.output_of(
                spawn.run_dispatch, self.dispatch_args(), self.parent_conv()
            )
        self.assertEqual(self.posts, [])
        self.assertIn('"receipt": "accepted"', receipt)
        self.assertIn('"reconciled": true', receipt)

    def test_rejected_dispatch_is_recorded_and_not_retried(self) -> None:
        with patch.object(transport, "api",
            side_effect=SystemExit("HTTP 422 POST /api/conversations: bad request"),
        ), self.assertRaisesRegex(SystemExit, "HTTP 422"):
            self.output_of(
                spawn.run_dispatch, self.dispatch_args(), self.parent_conv()
            )
        self.assertEqual(spawn.load_ledger(PARENT)["req-aaa1"]["status"], "rejected")
        with patch.object(transport, "api", side_effect=api_recorder({}, self.posts)
        ), self.assertRaisesRegex(SystemExit, "previously rejected"):
            spawn.run_dispatch(self.dispatch_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_active_ledger_dispatch_blocks_second_request_until_forced(self) -> None:
        self.bind_target(status="accepted")
        convs = {
            TARGET: self.child_conv(cid=TARGET, status="running"),
            CHILD: self.child_conv(cid=CHILD, status="running"),
        }
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
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
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            out = self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
        self.assertEqual(self.posts, [f"/api/conversations/{TARGET}/events"])
        self.assertIn('"receipt": "accepted"', out)
        self.assertIn('"operation": "resume"', out)
        self.assertIn(TARGET, out)

    def test_resume_posts_role_style_event_with_full_continuation_text(self) -> None:
        prompt = "resume: continue hop 2 with request req-res1 details"
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        bodies: list = []
        with patch.object(transport, "api",
            side_effect=body_capturing_recorder(convs, self.posts, bodies),
        ):
            self.output_of(
                spawn.run_resume,
                self.resume_args(prompt_file=self.prompt_file("resume49.txt", prompt)),
                self.parent_conv(),
            )
        self.assertEqual(self.posts, [f"/api/conversations/{TARGET}/events"])
        self.assertEqual(len(bodies), 1)
        persisted = bodies[0]["content"]
        self.assertTrue(persisted)
        # The full continuation text lands verbatim, prefixed only by the
        # #56 delivery sentinel demanded by the post-POST readback.
        self.assertTrue(persisted[0]["text"].startswith(prompt))
        self.assertRegex(persisted[0]["text"], r"delivery-marker: [0-9a-f]{12}$")
        self.assertEqual(bodies[0]["role"], "user")
        self.assertIs(bodies[0]["run"], True)
        self.assertNotIn("llm_message", bodies[0])

    def test_resume_rejects_missing_target(self) -> None:
        with patch.object(transport, "api", side_effect=api_recorder({}, self.posts)):
            with self.assertRaisesRegex(SystemExit, "does not exist"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_non_direct_child(self) -> None:
        convs = {
            TARGET: self.child_conv(
                cid=TARGET, status="finished", parent_conversation_id=OTHER
            )
        }
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "direct child"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_wrong_department(self) -> None:
        convs = {
            TARGET: self.child_conv(
                cid=TARGET, status="finished", tags={"clientsource": "agentcanvas", "department": "acceptance"}
            )
        }
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
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
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "workspace"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_missing_clientsource_tag(self) -> None:
        convs = {
            TARGET: self.child_conv(
                cid=TARGET, status="finished", tags={"department": "delivery"}
            )
        }
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "clientsource"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_active_target_without_concurrent_run(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="running")}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "active"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_stopped_target_without_silent_success(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="stopped")}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "stopped"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_rejects_child_unbound_in_ledger(self) -> None:
        ledger = spawn.load_ledger(PARENT)
        ledger.pop("req-disp0")
        spawn.save_ledger(PARENT, ledger)
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "authorized department child"):
                spawn.run_resume(self.resume_args(), self.parent_conv(), PARENT)
        self.assertEqual(self.posts, [])

    def test_resume_ticket_mismatch_is_rejected(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "ticket"):
                spawn.run_resume(
                    self.resume_args(ticket="#42"), self.parent_conv(), PARENT
                )
        self.assertEqual(self.posts, [])

    def test_resume_error_target_allows_single_bounded_attempt(self) -> None:
        convs = {TARGET: self.child_conv(cid=TARGET, status="error")}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
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
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
        entry = spawn.load_ledger(PARENT)["req-res1"]
        self.assertEqual(entry["status"], "unknown")
        self.assertEqual(entry["target_id"], TARGET)
        convs = {TARGET: self.child_conv(cid=TARGET, status="running")}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            receipt = self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
        self.assertEqual(self.posts, [])
        self.assertIn('"receipt": "accepted"', receipt)
        self.assertIn('"reconciled": true', receipt)

    def test_resume_unknown_still_finished_resends_once_then_unknown(self) -> None:
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_resume, self.resume_args(), self.parent_conv()
            )
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
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

    def test_unknown_resume_reconciles_from_persisted_event_marker(self) -> None:
        prompt = "resume: continue hop 2 for #51 without a request line"
        args = self.resume_args(prompt_file=self.prompt_file("resume51.txt", prompt))
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(spawn.run_resume, args, self.parent_conv())
        entry = spawn.load_ledger(PARENT)["req-res1"]
        self.assertEqual(entry["status"], "unknown")
        convs = {TARGET: self.child_conv(cid=TARGET, status="finished")}
        events = {
            TARGET: [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ]
        }
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts, events)
        ):
            receipt = self.output_of(spawn.run_resume, args, self.parent_conv())
        self.assertEqual(self.posts, [])
        self.assertIn('"receipt": "accepted"', receipt)
        self.assertIn('"reconciled": true', receipt)
        reconciled = spawn.load_ledger(PARENT)["req-res1"]
        self.assertEqual(reconciled["status"], "accepted")
        self.assertIn("marker", reconciled["evidence"])

    def test_resume_socket_timeout_yields_unknown_receipt(self) -> None:
        class StallHandler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                import time

                time.sleep(5)

        server = socketserver.TCPServer(("127.0.0.1", 0), StallHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = transport.BASE
        try:
            transport.BASE = f"http://127.0.0.1:{port}"

            def slow_urlopen(req, timeout=None):
                return REAL_URLOPEN(req, timeout=1)

            with patch.object(transport, "session_key", return_value="test-key"), patch.object(transport, "urlopen", slow_urlopen
            ), self.assertRaises((SystemExit, TimeoutError)):
                self.output_of(
                    spawn.run_resume, self.resume_args(), self.parent_conv()
                )
        finally:
            transport.BASE = base
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
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            out = self.output_of(
                spawn.run_notify,
                self.notify_args(related_request_id="req-not1"),
                self.child_window(),
                CHILD,
            )
        self.assertIn(f"/api/conversations/{PARENT}/events", self.posts)
        self.assertIn('"receipt": "accepted"', out)

    def test_notify_posts_role_style_event_with_full_report_text(self) -> None:
        report = (
            "engineering:report\ndepartment: delivery\nticket: #41\n"
            "hop: done with details\nrequest: req-not1\n"
        )
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        bodies: list = []
        with patch.object(transport, "api",
            side_effect=body_capturing_recorder(convs, self.posts, bodies),
        ):
            self.output_of(
                spawn.run_notify,
                self.notify_args(
                    related_request_id="req-not1",
                    prompt_file=self.prompt_file("report49.txt", report),
                ),
                self.child_window(),
                CHILD,
            )
        self.assertIn(f"/api/conversations/{PARENT}/events", self.posts)
        self.assertEqual(len(bodies), 1)
        persisted = bodies[0]["content"]
        self.assertTrue(persisted)
        # The full report text lands verbatim; the delivery sentinel (#56)
        # is appended for the post-POST readback and must not displace it.
        self.assertTrue(persisted[0]["text"].startswith(report))
        self.assertRegex(persisted[0]["text"], r"delivery-marker: [0-9a-f]{12}$")
        self.assertEqual(bodies[0]["role"], "user")
        self.assertIs(bodies[0]["run"], True)
        self.assertNotIn("llm_message", bodies[0])

    def test_empty_content_readback_is_judged_undelivered(self) -> None:
        # Issue #49/#56: the backend accepts the event POST yet persists the
        # user MessageEvent with empty llm_message.content, silently dropping
        # the text. Acceptance alone must never read as delivered: the
        # readback routes the delivery through the unknown/ledger path and
        # exits non-zero.
        convs = {PARENT: {"id": PARENT, "status": "running"}}

        def persist_empty(cid: str, body: dict) -> dict:
            return {
                "kind": "MessageEvent",
                "source": "user",
                "llm_message": {**body, "content": []},
            }

        recorder = api_recorder(convs, self.posts, None, persist=persist_empty)
        receipt_stream = io.StringIO()
        with patch.object(transport, "api", side_effect=recorder), \
                redirect_stdout(receipt_stream), self.assertRaises(SystemExit):
            spawn.run_notify(
                self.notify_args(related_request_id="req-not1"),
                self.child_window(),
                CHILD,
            )
        self.assertIn(f"/api/conversations/{PARENT}/events", self.posts)
        receipts = receipt_stream.getvalue()
        # The POST's provisional "accepted by API response" receipt is fine;
        # the FINAL receipt after readback must be unknown, never accepted.
        self.assertIn("accepted by API response", receipts)
        self.assertIn('"receipt": "unknown"', receipts)
        self.assertIn("empty content", receipts)
        final_receipts = [
            json.loads(block)
            for block in receipts.strip().replace("}\n{", "}\r{").split("\r")
        ]
        # First receipt: provisional POST acceptance (legitimate). Final
        # receipt: the readback adjudication, which must be unknown.
        self.assertEqual("accepted", final_receipts[0]["receipt"])
        self.assertEqual("unknown", final_receipts[-1]["receipt"])
        entry = spawn.load_ledger(PARENT)["req-report1"]
        self.assertEqual(entry["status"], "unknown")
        self.assertIn("empty content", entry["evidence"])
        self.assertEqual(entry["attempts"], 1)

    def test_readback_failure_variants_are_judged_undelivered(self) -> None:
        # Same seam, remaining readback failure shapes (#56): the POST is
        # accepted but the newest user MessageEvent either carries a stale
        # text without this delivery's sentinel, or never persists at all.
        # Both must be judged undelivered, never accepted.
        convs = {PARENT: {"id": PARENT, "status": "running"}}

        def persist_stale(cid: str, body: dict) -> dict:
            return {
                "kind": "MessageEvent",
                "source": "user",
                "llm_message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "stale sibling delivery text"}
                    ],
                },
            }

        def persist_nothing(cid: str, body: dict) -> None:
            return None

        cases = (
            ("sentinel-missing", persist_stale, "missing from"),
            ("event-not-persisted", persist_nothing, "not found or events read failed"),
        )
        for label, persist, evidence_needle in cases:
            with self.subTest(variant=label):
                posts: list = []
                request_id = f"req-rb-{label}"
                recorder = api_recorder(convs, posts, None, persist=persist)
                receipt_stream = io.StringIO()
                with patch.object(transport, "api", side_effect=recorder), \
                        redirect_stdout(receipt_stream), \
                        self.assertRaises(SystemExit):
                    spawn.run_notify(
                        self.notify_args(
                            request_id=request_id,
                            related_request_id="req-not1",
                        ),
                        self.child_window(),
                        CHILD,
                    )
                self.assertIn(f"/api/conversations/{PARENT}/events", posts)
                self.assertIn('"receipt": "unknown"', receipt_stream.getvalue())
                entry = spawn.load_ledger(PARENT)[request_id]
                self.assertEqual(entry["status"], "unknown")
                self.assertIn(evidence_needle, entry["evidence"])

    def test_related_request_mismatch_rejected_without_post(self) -> None:
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
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
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
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
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
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
        with patch.object(transport, "api", side_effect=api_recorder({}, self.posts)):
            with self.assertRaisesRegex(SystemExit, "Planning must not notify"):
                spawn.run_notify(
                    self.notify_args(), self.parent_conv(), PARENT
                )
        self.assertEqual(self.posts, [])

    def test_employee_layer_caller_is_refused_before_post(self) -> None:
        conv = self.child_window()
        conv["tags"]["layer"] = "employee"
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)):
            with self.assertRaisesRegex(SystemExit, "not a department child"):
                spawn.run_notify(self.notify_args(), conv, CHILD)
        self.assertEqual(self.posts, [])
        self.assertNotIn("req-report1", spawn.load_ledger(PARENT))

    def test_unknown_notify_reconciles_marker_without_second_post(self) -> None:
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        entry = spawn.load_ledger(PARENT)["req-report1"]
        self.assertEqual(entry["status"], "unknown")
        with open(
            self.notify_args().prompt_file, encoding="utf-8"
        ) as fh:
            report = fh.read()
        events = {
            PARENT: [
                {"role": "user", "content": [{"type": "text", "text": report}]}
            ]
        }
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts, events)
        ):
            receipt = self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        self.assertEqual(self.posts, [])
        self.assertIn('"receipt": "accepted"', receipt)
        self.assertIn('"reconciled": true', receipt)
        reconciled = spawn.load_ledger(PARENT)["req-report1"]
        self.assertEqual(reconciled["status"], "accepted")
        self.assertIn("marker", reconciled["evidence"])
        self.assertEqual(reconciled["attempts"], 1)

    def test_events_lookup_uses_conversation_scoped_search_shape(self) -> None:
        # Issue #53: the events read must use the conversation-scoped search
        # endpoint — the bare /events form is rejected by the server (422),
        # which silently disabled reconcile-before-resend.
        search = spawn.notify.event_search_path(PARENT)
        self.assertTrue(search.startswith(f"/api/conversations/{PARENT}/events/search?"))
        self.assertIn("limit=", search)
        self.assertIn("sort_order=", search)
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        with open(self.notify_args().prompt_file, encoding="utf-8") as fh:
            report = fh.read()
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        events = {
            PARENT: [{"role": "user", "content": [{"type": "text", "text": report}]}]
        }
        calls: list = []
        base = api_recorder(convs, self.posts, events)

        def spy(method, path, body=None, timeout=60, redact_error=False):
            calls.append((method, path))
            return base(method, path, body, timeout, redact_error)

        with patch.object(transport, "api", side_effect=spy):
            receipt = self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        self.assertIn(("GET", search), calls)
        self.assertNotIn(("GET", f"/api/conversations/{PARENT}/events"), calls)
        # The marker was found through the search read: no re-send fires.
        self.assertNotIn(("POST", f"/api/conversations/{PARENT}/events"), calls)
        self.assertIn('"reconciled": true', receipt)
        self.assertEqual(spawn.load_ledger(PARENT)["req-report1"]["attempts"], 1)


class TransportErrorLedgerTests(LedgerIsolatedTestCase):
    """Issue #53: connection-loss produces a ledger record, retry is bounded.

    RemoteDisconnected (and other http.client.HTTPException transport
    failures) used to escape http_op without a ledger record, so
    reconciliation could not tell "accepted but response lost" from
    "never sent".
    """

    def setUp(self) -> None:
        super().setUp()
        self.bind_target()
        ledger_map = spawn.load_ledger(PARENT)
        entry = ledger_map.pop("req-disp0")
        entry["request_id"] = "req-not1"
        entry["child_id"] = CHILD
        ledger_map["req-not1"] = entry
        spawn.save_ledger(PARENT, ledger_map)
        self.first_post = None
        self.inner_api = transport.api

    def record_posts(self) -> None:
        """Capture the first POST path/body through any inner api patch."""
        outer = self

        def delegating(method: str, path: str, body=None, **kw):
            if method == "POST" and outer.first_post is None:
                outer.first_post = (method, path, body)
            # Delegate to whatever api implementation is current at call
            # time, so per-phase patches in the same test still apply.
            return outer.inner_api(method, path, body, **kw)

        self.api_patch = patch.object(
            transport, "api", new=lambda *a, **kw: delegating(*a, **kw)
        )
        self.api_patch.start()
        self.addCleanup(self.api_patch.stop)
        self.addCleanup(setattr, transport, "api", self.inner_api)

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
                "engineering:report\ndepartment: delivery\nticket: #41\n"
                "hop: done\nrequest: req-not1\n",
            ),
            max_iterations=500,
            poll_sec=0,
            timeout_sec=5400,
            force=False,
            ticket="",
            request_id="req-report1",
            target_id="",
            related_request_id="",
            parent_id="",
        )
        base.update(over)
        return argparse.Namespace(**base)

    def test_remote_disconnected_is_ledgered_with_bounded_resend(self) -> None:
        drop = http.client.RemoteDisconnected("dropped mid-response")
        self.record_posts()
        with patch.object(transport, "api", side_effect=drop), \
                self.assertRaises(http.client.RemoteDisconnected):
            receipt = self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        self.assertIsNone(self.first_post)
        entry = spawn.load_ledger(PARENT)["req-report1"]
        self.assertEqual(entry["status"], "unknown")
        self.assertEqual(entry["attempts"], 1)
        # Exactly one ledger-gated re-send fires before the bound is reached.
        # The first attempt's lost POST is proven absent here: first_post
        # only populates now, on the re-send, never during the failed turn.
        # The re-send itself also hits the same dropped connection, so this
        # second unknown stays un-accepted (bounded, never blind-accepted).
        # The events-search GET still succeeds (marker absent -> resend);
        # the recorder captures the re-send's POST path/body before the
        # connection drops again.
        drop = http.client.RemoteDisconnected("dropped mid-response")

        def record_then_drop(method, path, body=None, **kw):
            if method != "POST":
                return {"items": []}
            if self.first_post is None:
                self.first_post = (method, path, body)
            raise drop

        receipt_stream = io.StringIO()
        with patch.object(transport, "api", new=record_then_drop), \
                redirect_stdout(receipt_stream), \
                self.assertRaises(http.client.RemoteDisconnected):
            spawn.run_notify(self.notify_args(), self.child_window(), CHILD)
        receipt = receipt_stream.getvalue()
        self.assertIsNotNone(self.first_post)
        self.assertEqual(self.first_post[0], "POST")
        self.assertEqual(self.first_post[2].get("role"), "user")
        self.assertEqual(self.first_post[1], f"/api/conversations/{PARENT}/events")
        self.assertIn('"receipt": "unknown"', receipt)
        self.assertIn("RemoteDisconnected/HTTP failure", receipt)
        self.assertNotIn("dropped mid-response", receipt)
        entry = spawn.load_ledger(PARENT)["req-report1"]
        self.assertEqual(entry["attempts"], 2)
        # Bound exhausted: a third same-request attempt reconciles the
        # (still undelivered) marker through the events search read, POSTs
        # nothing, and fails closed with the exhausted receipt.
        bound_calls: list = []
        bound_base = api_recorder({}, self.posts, {PARENT: []})

        def bound_spy(method, path, body=None, timeout=60, redact_error=False):
            bound_calls.append((method, path))
            return bound_base(method, path, body, timeout, redact_error)

        with patch.object(transport, "api", side_effect=bound_spy), \
                self.assertRaises(SystemExit):
            self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        self.assertEqual(
            [call for call in bound_calls if call[0] == "POST"], []
        )
        self.assertEqual(spawn.load_ledger(PARENT)["req-report1"]["attempts"], 2)
        self.assertEqual(spawn.load_ledger(PARENT)["req-report1"]["status"], "unknown")

    def test_http_op_classifies_transport_errors_fail_closed(self) -> None:
        cases = (
            http.client.RemoteDisconnected("dropped mid-response"),
            http.client.BadStatusLine("''"),
        )
        for exc in cases:
            for redact in (False, True):
                with self.subTest(exc=type(exc).__name__, redact=redact), \
                        patch.object(transport, "api", side_effect=exc):
                    payload, receipt, error = ledger.http_op(
                        "POST",
                        f"/api/conversations/{PARENT}/events",
                        {"role": "user"},
                        redact_error=redact,
                        operation="notify",
                        request_id="req-tx1",
                        ticket="#53",
                        parent_id=PARENT,
                        target_id=CHILD,
                        emit=False,
                    )
                    self.assertIsNone(payload)
                    self.assertIs(error, exc)
                    self.assertEqual(receipt["receipt"], "unknown")
                    serialized = json.dumps(receipt)
                    self.assertNotIn("dropped mid-response", serialized)
                    self.assertNotIn("''", serialized)
                    if redact:
                        self.assertIn("redacted", receipt["evidence"])
                    else:
                        self.assertIn(
                            "RemoteDisconnected/HTTP failure",
                            receipt["evidence"],
                        )
                        self.assertIn(
                            "never claim exactly-once", receipt["evidence"]
                        )

    def test_http_op_retries_to_acceptance_within_bound(self) -> None:
        drop = http.client.RemoteDisconnected("dropped mid-response")
        calls = []

        def drop_then_accept(method, path, body=None, **kw):
            calls.append((method, path))
            if len(calls) < ledger.MAX_HTTP_OP_ATTEMPTS:
                raise drop
            return {"ok": True}

        with patch.object(transport, "api", side_effect=drop_then_accept):
            for attempt in range(ledger.MAX_HTTP_OP_ATTEMPTS):
                payload, receipt, error = ledger.http_op(
                    "POST",
                    f"/api/conversations/{PARENT}/events",
                    {"role": "user"},
                    redact_error=False,
                    operation="notify",
                    request_id="req-tx2",
                    ticket="#53",
                    parent_id=PARENT,
                    target_id=CHILD,
                    emit=False,
                )
                if error is None:
                    break
        self.assertIsNone(error)
        self.assertEqual(receipt["receipt"], "accepted")
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(len(calls), ledger.MAX_HTTP_OP_ATTEMPTS)

    def test_http_op_retry_is_bounded(self) -> None:
        drop = http.client.RemoteDisconnected("dropped mid-response")
        with patch.object(transport, "api", side_effect=drop):
            for _ in range(ledger.MAX_HTTP_OP_ATTEMPTS + 1):
                payload, receipt, error = ledger.http_op(
                    "POST",
                    f"/api/conversations/{PARENT}/events",
                    {"role": "user"},
                    redact_error=False,
                    operation="notify",
                    request_id="req-tx3",
                    ticket="#53",
                    parent_id=PARENT,
                    target_id=CHILD,
                    emit=False,
                )
                self.assertIs(error, drop)
                self.assertEqual(receipt["receipt"], "unknown")

    def test_unknown_notify_without_marker_resends_exactly_once(self) -> None:
        convs = {PARENT: {"id": PARENT, "status": "running"}}
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        # Marker genuinely absent: the first attempt never landed, so the
        # reconcile returns "resend" and the single bounded re-send fires.
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts, {PARENT: []})
        ):
            receipt = self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        self.assertEqual(
            self.posts.count(f"/api/conversations/{PARENT}/events"), 1
        )
        self.assertIn('"receipt": "accepted"', receipt)
        # The delivered report replays reconciled instead of duplicating:
        # dedup wins even at exhausted attempts.
        before = self.posts.count(f"/api/conversations/{PARENT}/events")
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts, {PARENT: []})
        ):
            replay = self.output_of(
                spawn.run_notify, self.notify_args(), self.child_window(), CHILD
            )
        self.assertEqual(
            self.posts.count(f"/api/conversations/{PARENT}/events"), before
        )
        self.assertIn('"receipt": "accepted"', replay)
        self.assertIn('"reconciled": true', replay)
        # Exhaustion is the pure lost-response path on a fresh identity
        # (two timeouts, no API acceptance, marker never appears):
        # unknown + exit 1 is kept.
        exhaust_report = (
            "engineering:report\ndepartment: delivery\nticket: #41\n"
            "hop: done\nrequest: req-not1\n"
        )
        exhaust_args = self.notify_args(
            request_id="req-report2",
            prompt_file=self.prompt_file("report-exhaust.txt", exhaust_report),
        )
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_notify, exhaust_args, self.child_window(), CHILD
            )
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(TimeoutError):
            self.output_of(
                spawn.run_notify, exhaust_args, self.child_window(), CHILD
            )
        with patch.object(transport, "api", side_effect=TimeoutError("read timed out")
        ), self.assertRaises(SystemExit):
            self.output_of(
                spawn.run_notify, exhaust_args, self.child_window(), CHILD
            )
        self.assertEqual(
            self.posts.count(f"/api/conversations/{PARENT}/events"), before
        )
        exhausted = spawn.load_ledger(PARENT)["req-report2"]
        self.assertEqual(exhausted["status"], "unknown")
        self.assertEqual(exhausted["attempts"], 2)


class ParallelSameDirRoundTripTests(LedgerIsolatedTestCase):
    """Issue #53: parallel same-working_dir dispatch+notify stays bound.

    Two planning windows share one imported working_dir. The old resolver
    silently picked the most recently updated same-dir conversation, so a
    child's notify landed on the previous conversation. Regression contract:

    - dispatch/notify never act on a silently-resolved identity: without an
      explicit id they fail closed before any lookup or POST;
    - two same-dir candidates make even the read-only heuristic fail closed
      instead of deterministically resolving the previous conversation;
    - explicit id binding wins: the parent ledger entry records the real
      child, the child carries its own id (env + tag), and notify's
      ``--parent-id`` cross-check rejects a foreign parent before posting.
    """

    def setUp(self) -> None:
        super().setUp()
        self.wd_b = os.path.join(self.tmp, "proj-b")
        os.makedirs(self.wd_b, exist_ok=True)
        parent_a = self.parent_conv()
        parent_b = self.parent_conv(id=OTHER, working_dir=self.wd_b)
        self.parents = {PARENT: parent_a, OTHER: parent_b}
        self.saved_conversation_id = os.environ.get("OPENHANDS_CONVERSATION_ID")
        os.environ["OPENHANDS_CONVERSATION_ID"] = ""

    def tearDown(self) -> None:
        if self.saved_conversation_id is None:
            os.environ.pop("OPENHANDS_CONVERSATION_ID", None)
        else:
            os.environ["OPENHANDS_CONVERSATION_ID"] = self.saved_conversation_id
        super().tearDown()

    def child_window(self, cid: str, parent_id: str, **over) -> dict:
        conv = {
            "id": cid,
            "workspace": {"kind": "LocalWorkspace", "working_dir": self.wd},
            "tags": {"clientsource": "agentcanvas", "department": "delivery"},
            "parent_conversation_id": parent_id,
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
            prompt_file=self.prompt_file("task.txt", "continue ticket #53 work"),
            max_iterations=500,
            poll_sec=0,
            timeout_sec=5400,
            force=False,
            ticket="#53",
            request_id="req-p53a",
            target_id="",
            related_request_id="",
        )
        base.update(over)
        return argparse.Namespace(**base)

    def notify_args(self, **over):
        base = dict(
            mode="notify",
            this_id="",
            profile_id="",
            department="",
            github_token_secret="",
            prompt_file=self.prompt_file(
                "report.txt",
                "engineering:report\ndepartment: delivery\nticket: #53\n"
                "hop: done\nrequest: req-p53a\n",
            ),
            max_iterations=500,
            poll_sec=0,
            timeout_sec=5400,
            force=False,
            ticket="",
            request_id="req-p53n",
            target_id="",
            related_request_id="",
            parent_id="",
        )
        base.update(over)
        return argparse.Namespace(**base)

    def last_json(self, text: str) -> dict:
        """Parse the last JSON object printed on a receipt stream."""
        decoder = json.JSONDecoder()
        idx = 0
        result: dict = {}
        while idx < len(text):
            while idx < len(text) and text[idx] in " \t\r\n":
                idx += 1
            if idx >= len(text):
                break
            result, idx = decoder.raw_decode(text, idx)
        return result

    def run_main_gate(self, mode: str) -> None:
        """Drive real main() with no --this-id and no conversation env.

        Args:
            mode: CLI mode under test ("dispatch" or "notify").
        """
        original_api = transport.api
        original_argv = sys.argv
        saved = {
            key: os.environ.get(key)
            for key in ("OPENHANDS_CONVERSATION_ID", "CONVERSATION_ID")
        }
        for key in saved:
            os.environ.pop(key, None)
        api_calls: list = []

        def counting(method, path, body=None, timeout=60, redact_error=False):
            api_calls.append((method, path))
            return {"items": []}

        output = io.StringIO()
        try:
            transport.api = counting
            with tempfile.TemporaryDirectory() as raw:
                prompt_path = Path(raw) / "prompt.txt"
                prompt_path.write_text("deliver issue 53", encoding="utf-8")
                sys.argv = ["spawn.py", "--mode", mode, "--profile-id", PROFILE,
                            "--prompt-file", str(prompt_path)]
                with redirect_stdout(output):
                    with self.assertRaisesRegex(
                        SystemExit, "requires an explicit conversation id"
                    ):
                        spawn.main()
        finally:
            transport.api = original_api
            sys.argv = original_argv
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(api_calls, [])

    def test_mutating_modes_fail_closed_without_explicit_identity(self) -> None:
        # The cwd heuristic would "resolve" something here; main() must
        # refuse dispatch/notify without --this-id / env before any lookup.
        with patch.object(identity, "cwd_match_paths", return_value=[self.wd]):
            self.run_main_gate("dispatch")
            self.run_main_gate("notify")
        self.assertEqual(self.posts, [])
        self.assertEqual(spawn.load_ledger(PARENT), {})
        self.assertEqual(spawn.load_ledger(OTHER), {})

    def test_heuristic_fails_closed_on_two_same_dir_candidates(self) -> None:
        # The previous behavior picked updated_at max here — deterministically
        # the *other* conversation under parallel same-dir runs.
        items = [
            {
                "id": PARENT,
                "workspace": {"working_dir": self.wd},
                "tags": {"clientsource": "agentcanvas"},
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": OTHER,
                "workspace": {"working_dir": self.wd},
                "tags": {"clientsource": "agentcanvas"},
                "updated_at": "2026-01-02T00:00:00Z",
            },
        ]
        want = identity.norm_path(self.wd)
        with self.assertRaisesRegex(SystemExit, "workspace identity is ambiguous"):
            identity.pick_workspace_id(items, want)
        self.assertEqual(
            identity.workspace_candidates(items, want), [PARENT, OTHER]
        )
        with patch.object(identity, "cwd_match_paths", return_value=[want]), \
            patch.object(identity, "search_running", return_value=items):
            with self.assertRaisesRegex(SystemExit, "workspace identity is ambiguous"):
                spawn.resolve_this(None)

    def test_parallel_dispatch_and_notify_round_trip_with_explicit_ids(self) -> None:
        # Issue #53: the child id is derived from the dispatching parent, so
        # two same-dir windows can never produce the same child; each create
        # body carries its own id (env + tag) and its own parent.
        child_a_id = identity.dispatch_request_child_id(
            PARENT, "delivery", "#53", "req-p53a"
        )
        child_b_id = identity.dispatch_request_child_id(
            OTHER, "delivery", "#53", "req-p53b"
        )
        self.assertNotEqual(child_a_id, child_b_id)
        events: dict = {PARENT: [], OTHER: []}
        convs = {
            **self.parents,
            child_a_id: self.child_window(child_a_id, PARENT),
            child_b_id: self.child_window(child_b_id, OTHER, working_dir=self.wd_b),
        }
        create_bodies: list = []
        recorder = body_capturing_recorder(
            convs, self.posts, [], creates=create_bodies
        )
        with patch.object(transport, "api", side_effect=recorder):
            # Two dispatches from the two same-dir planning windows: explicit
            # ids bind each request; each child gets its own derived id,
            # never an accidental shared resolution.
            receipt_a = self.output_of(
                spawn.run_dispatch,
                self.dispatch_args(),
                self.parents[PARENT],
                PARENT,
            )
            receipt_b = self.output_of(
                spawn.run_dispatch,
                self.dispatch_args(request_id="req-p53b"),
                self.parents[OTHER],
                OTHER,
            )
            self.assertEqual(
                self.last_json(receipt_a)["child_conversation_id"], child_a_id
            )
            self.assertEqual(self.last_json(receipt_a)["id"], child_a_id)
            self.assertEqual(
                self.last_json(receipt_b)["child_conversation_id"], child_b_id
            )
            self.assertEqual(self.last_json(receipt_b)["id"], child_b_id)
            ledger_a = spawn.load_ledger(PARENT)["req-p53a"]
            self.assertEqual(ledger_a["child_id"], child_a_id)
            self.assertEqual(ledger_a["parent_id"], PARENT)
            self.assertEqual(ledger_a["status"], "accepted")
            ledger_b = spawn.load_ledger(OTHER)["req-p53b"]
            self.assertEqual(ledger_b["child_id"], child_b_id)
            self.assertEqual(ledger_b["parent_id"], OTHER)

            # The dispatch injected the child's own identity into the create
            # body: OPENHANDS_CONVERSATION_ID env + conversation_id tag, and
            # the parent field of each child names its own window.
            self.assertEqual(len(create_bodies), 2)
            body_a, body_b = create_bodies
            self.assertEqual(body_a["conversation_id"], child_a_id)
            self.assertEqual(body_a["parent_conversation_id"], PARENT)
            self.assertEqual(
                body_a["env"]["OPENHANDS_CONVERSATION_ID"], child_a_id
            )
            self.assertEqual(body_a["tags"]["conversation_id"], child_a_id)
            self.assertEqual(body_b["conversation_id"], child_b_id)
            self.assertEqual(body_b["parent_conversation_id"], OTHER)
            self.assertEqual(
                body_b["env"]["OPENHANDS_CONVERSATION_ID"], child_b_id
            )
            self.assertEqual(body_b["tags"]["conversation_id"], child_b_id)
            self.assertNotEqual(
                body_a["env"]["OPENHANDS_CONVERSATION_ID"],
                body_b["env"]["OPENHANDS_CONVERSATION_ID"],
            )

            # Child A reports with --parent-id PARENT; the cross-check passes
            # and the report lands on its real parent.
            report_args = self.notify_args(
                related_request_id="req-p53a",
                parent_id=PARENT,
            )
            out = self.output_of(
                spawn.run_notify, report_args, convs[child_a_id], child_a_id
            )
            self.assertIn('"receipt": "accepted"', out)
            self.assertEqual(
                self.posts.count(f"/api/conversations/{PARENT}/events"), 1
            )
            self.assertNotIn(
                f"/api/conversations/{OTHER}/events", self.posts
            )

            # The same report claiming the WRONG (previous/parallel) parent is
            # refused fail-closed before any lookup or POST.
            wrong = self.notify_args(
                related_request_id="req-p53a", parent_id=OTHER
            )
            with self.assertRaisesRegex(SystemExit, "does not match"):
                spawn.run_notify(wrong, convs[child_a_id], child_a_id)
            self.assertEqual(
                self.posts.count(f"/api/conversations/{PARENT}/events"), 1
            )
            self.assertNotIn(
                f"/api/conversations/{OTHER}/events", self.posts
            )

            # Env identity wins over the stale heuristic too: the dispatch-
            # injected OPENHANDS_CONVERSATION_ID resolves this child even with
            # two same-working_dir candidates, and notify cross-checks it.
            with patch.dict(
                os.environ, {"OPENHANDS_CONVERSATION_ID": child_a_id}
            ):
                resolved = spawn.resolve_this(None)
            self.assertEqual(resolved, child_a_id)
            with patch.dict(
                os.environ, {"OPENHANDS_CONVERSATION_ID": child_b_id}
            ):
                resolved = spawn.resolve_this(None)
            self.assertEqual(resolved, child_b_id)


class ControlledHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Deterministic local HTTP adapter fixture for subprocess tests."""

    daemon_threads = True


class ControlledHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Serve the minimal conversation API used by the CLI operations."""

    server: ControlledHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        self.server.requests.append(("GET", self.path))
        conversations = {
            f"/api/conversations/{PARENT}": {
                "id": PARENT,
                "workspace": {
                    "kind": "LocalWorkspace",
                    "working_dir": self.server.working_dir,
                },
                "tags": {"clientsource": "agentcanvas"},
            },
            f"/api/conversations/{CHILD}": {
                "id": CHILD,
                "workspace": {
                    "kind": "LocalWorkspace",
                    "working_dir": self.server.working_dir,
                },
                "tags": {
                    "clientsource": "agentcanvas",
                    "department": "delivery",
                },
                "parent_conversation_id": PARENT,
                "status": "finished",
            },
        }
        payload = conversations.get(self.path)
        if payload is not None:
            self._json(200, payload)
            return
        if self.path.startswith(f"/api/conversations/{CHILD}/events/search"):
            items = []
            if self.server.events_posted:
                body = json.loads(self.server.events_posted.decode("utf-8"))
                items = [
                    {"kind": "MessageEvent", "source": "user", "llm_message": body}
                ]
            self._json(200, {"items": items})
            return
        if self.path.startswith(f"/api/conversations/{PARENT}/events/search"):
            items = []
            if self.server.notify_posted:
                body = json.loads(self.server.notify_posted.decode("utf-8"))
                items = [
                    {"kind": "MessageEvent", "source": "user", "llm_message": body}
                ]
            self._json(200, {"items": items})
            return
        self._json(404, {"detail": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        self.server.requests.append(("POST", self.path, body))
        if self.path == "/api/conversations":
            self._json(200, {"id": CHILD, "conversation_id": CHILD})
        elif self.path == f"/api/conversations/{CHILD}/events":
            self.server.events_posted = body
            self._json(200, {"accepted": True})
        elif self.path == f"/api/conversations/{PARENT}/events":
            self.server.notify_posted = body
            self._json(200, {"accepted": True})
        else:
            self._json(404, {"detail": "not found"})


class ProcessCompletionAcceptanceTests(unittest.TestCase):
    """Verify real HTTP adapter and CLI process completion semantics."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="spawn41-http-")
        self.working_dir = os.path.join(self.tmp, "project")
        os.makedirs(self.working_dir)
        self.server = ControlledHTTPServer(("127.0.0.1", 0), ControlledHTTPHandler)
        self.server.working_dir = self.working_dir
        self.server.requests = []
        self.server.events_posted = None
        self.server.notify_posted = None
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *arguments: str) -> dict:
        environment = os.environ.copy()
        environment.update(
            {
                "OPENHANDS_URL": (
                    f"http://127.0.0.1:{self.server.server_address[1]}"
                ),
                "OPENHANDS_UI": "http://127.0.0.1:3001",
                "OPENHANDS_CONVERSATION_ID": "",
                "CONVERSATION_ID": "",
                "OPENHANDS_DISPATCH_LEDGER_DIR": os.path.join(
                    self.tmp, "ledger"
                ),
            }
        )
        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH), *arguments],
            cwd=self.working_dir,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"CLI failed: stdout={completed.stdout!r} stderr={completed.stderr!r}",
        )
        self.assertEqual(completed.stderr, "")
        decoder = json.JSONDecoder()
        remaining = completed.stdout.lstrip()
        reports = []
        while remaining:
            report, end = decoder.raw_decode(remaining)
            reports.append(report)
            remaining = remaining[end:].lstrip()
        self.assertGreaterEqual(len(reports), 2)
        for report in reports:
            self.assertEqual(report["receipt"], "accepted")
            self.assertIn("evidence", report)
        return reports[-1]

    def write_prompt(self, name: str, text: str) -> str:
        path = os.path.join(self.tmp, name)
        Path(path).write_text(text, encoding="utf-8")
        return path

    def test_dispatch_resume_notify_are_real_processes_with_no_post_success_calls(self) -> None:
        dispatch_prompt = self.write_prompt("dispatch.txt", "dispatch ticket #41")
        dispatch = self.run_cli(
            "--mode",
            "dispatch",
            "--this-id",
            PARENT,
            "--profile-id",
            PROFILE,
            "--department",
            "delivery",
            "--ticket",
            "#41",
            "--request-id",
            "req-dispatch",
            "--prompt-file",
            dispatch_prompt,
            "--poll-sec",
            "0",
        )
        self.assertEqual(dispatch["receipt"], "accepted")
        self.assertEqual(dispatch["operation"], "dispatch")
        self.assertEqual(
            self.server.requests[-1][0:2], ("POST", "/api/conversations")
        )

        resume_prompt = self.write_prompt("resume.txt", "resume ticket #41")
        resume = self.run_cli(
            "--mode",
            "resume",
            "--this-id",
            PARENT,
            "--target-id",
            CHILD,
            "--ticket",
            "#41",
            "--request-id",
            "req-resume",
            "--prompt-file",
            resume_prompt,
            "--poll-sec",
            "0",
        )
        self.assertEqual(resume["receipt"], "accepted")
        self.assertEqual(resume["operation"], "resume")
        # requests[-1] is the #56 post-POST readback GET; select the POST.
        resume_post = [
            request
            for request in self.server.requests
            if request[0] == "POST"
            and request[1] == f"/api/conversations/{CHILD}/events"
        ][-1]
        resume_body = json.loads(resume_post[2].decode("utf-8"))
        self.assertEqual(resume_body["role"], "user")
        self.assertIs(resume_body["run"], True)
        self.assertEqual(resume_body["content"][0]["type"], "text")
        self.assertTrue(resume_body["content"][0]["text"].startswith("resume ticket #41"))
        self.assertRegex(resume_body["content"][0]["text"], r"delivery-marker: [0-9a-f]{12}$")

        report = self.write_prompt(
            "report.txt",
            "engineering:report\ndepartment: delivery\nticket: #41\n"
            "hop: done\nrequest: req-dispatch\n",
        )
        notify = self.run_cli(
            "--mode",
            "notify",
            "--this-id",
            CHILD,
            "--ticket",
            "#41",
            "--request-id",
            "req-notify",
            "--related-request-id",
            "req-dispatch",
            "--prompt-file",
            report,
            "--poll-sec",
            "0",
        )
        self.assertEqual(notify["receipt"], "accepted")
        self.assertEqual(notify["operation"], "notify")
        # requests[-1] is the #56 post-POST readback GET; select the POST.
        notify_post = [
            request
            for request in self.server.requests
            if request[0] == "POST"
            and request[1] == f"/api/conversations/{PARENT}/events"
        ][-1]
        notify_body = json.loads(notify_post[2].decode("utf-8"))
        self.assertTrue(notify_body["content"])
        self.assertIn("request: req-dispatch", notify_body["content"][0]["text"])

        for operation in (dispatch, resume, notify):
            self.assertIsInstance(operation["evidence"], str)
            self.assertTrue(operation["evidence"])
        self.assertNotIn("/run", [request[1] for request in self.server.requests])



class CompletionSemanticsTests(LedgerIsolatedTestCase):
    """accepted receipt is emitted and the run returns when polling is off."""

    def test_accepted_dispatch_returns_immediately_with_receipt(self) -> None:
        recorder = api_recorder({CHILD: self.child_conv()}, self.posts)
        with patch.object(transport, "api", side_effect=recorder), patch.object(
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
        with patch.object(transport, "api", side_effect=api_recorder(convs, self.posts)), patch.object(
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
