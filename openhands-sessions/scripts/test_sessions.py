from __future__ import annotations

import contextlib
import importlib.util
import io
import json
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
from canvas_sessions import transport

# UUID conversation fixtures: ledger files are keyed by conversation UUID,
# so every id that touches the request-scoped ledger must be a UUID.
MAIN_PARENT_ID = "3f6d2a41-9c07-4b5e-8a2d-1e6f0a5b7c83"
MAIN_CHILD_ID = "a4b1c8e2-5f30-4d97-9b26-0c7e8d1a4f52"
MAIN_DISPATCH_ID = "d5e2f9a3-6c41-4ea8-b037-1d8f9e2b5a63"


class CredentialTests(unittest.TestCase):
    # GH_TOKEN-family keys that a managing agent window may already carry in
    # its ambient environment; the suite must be hermetic against them.
    AMBIENT_TOKEN_KEYS = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN")

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

    def neutralize_ambient_tokens(self):
        saved = {
            key: os.environ[key]
            for key in self.AMBIENT_TOKEN_KEYS
            if key in os.environ
        }
        for key in saved:
            os.environ.pop(key, None)
        return saved

    def restore_ambient_tokens(self, saved: dict[str, str]) -> None:
        os.environ.update(saved)

    def test_explicit_reference_injects_key_absent_at_startup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            gh = self.fake_gh(Path(raw))
            saved = self.neutralize_ambient_tokens()
            try:
                self.assertNotIn("GH_TOKEN", os.environ)
                self.assertEqual(
                    github_command.run_github_command(
                        "PROCESS_REGISTERED_GITHUB_KEY",
                        "available-on-reference",
                        [str(gh), "api", "user"],
                    ),
                    0,
                )
            finally:
                self.restore_ambient_tokens(saved)

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
            "hop": "done",
            "receipts": "delivery implement=pass",
            "suggested next": "分发 acceptance #24",
        }
        fields.update(overrides)
        return "engineering:report\n" + "\n".join(
            f"{key}: {value}" for key, value in fields.items()
        )

    def test_exact_report_correlation(self) -> None:
        self.assertEqual(spawn.validate_report(self.report(), self.child()), "exact")

    def test_mismatch_and_partial_legacy_are_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "identity mismatch"):
            spawn.validate_report(self.report(ticket="#23"), self.child())
        partial = (
            "engineering:report\n"
            "department: delivery\n"
            "hop: done\n"
            "receipts: delivery implement=pass\n"
            "suggested next: stop"
        )
        with self.assertRaisesRegex(SystemExit, "identity missing"):
            spawn.validate_report(partial, self.child(), True)

    def test_legacy_requires_complete_explicit_compatibility(self) -> None:
        legacy = (
            "engineering:report\n"
            "hop: done\n"
            "receipts: delivery implement=pass\n"
            "suggested next: stop"
        )
        with self.assertRaisesRegex(SystemExit, "identity missing"):
            spawn.validate_report(legacy, self.child())
        self.assertEqual(
            spawn.validate_report(legacy, self.child(), True), "legacy-unverified"
        )
        with self.assertRaisesRegex(SystemExit, "report envelope missing"):
            spawn.validate_report("engineering:report\nhop: done", self.child(), True)

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


class CanvasApi:
    def __init__(self) -> None:
        self.calls = []
        self.conversations = {
            MAIN_PARENT_ID: {
                "id": MAIN_PARENT_ID,
                "execution_status": "running",
                "workspace": {"kind": "LocalWorkspace", "working_dir": "C:/repo"},
                "tags": {"clientsource": "agentcanvas"},
            }
        }
        self.dispatch_tag_override = {}
        self.events: dict[str, list] = {}

    def __call__(self, method, path, body=None, timeout=60, redact_error=False):
        self.calls.append((method, path, body, timeout))
        if method == "GET" and path.split("?")[0].endswith("/events/search"):
            conversation_id = path.split("/")[3]
            items = list(reversed(self.events.get(conversation_id, [])))
            return json.loads(json.dumps({"items": items}))
        if method == "GET" and path.startswith("/api/conversations/search"):
            return {"items": []}
        if method == "GET" and path.startswith("/api/conversations/"):
            conversation_id = path.rsplit("/", 1)[-1]
            payload = self.conversations.get(conversation_id)
            if payload is None:
                raise SystemExit(f"HTTP 404 GET {path}: not found")
            return json.loads(json.dumps(payload))
        if method == "POST" and path == "/api/conversations":
            assert body is not None
            conversation_id = body["conversation_id"]
            tags = {**body["tags"], **self.dispatch_tag_override}
            self.conversations[conversation_id] = {
                "id": conversation_id,
                "conversation_id": conversation_id,
                "parent_conversation_id": body.get("parent_conversation_id"),
                "execution_status": "running",
                "workspace": body["workspace"],
                "tags": tags,
            }
            return {"id": conversation_id}
        if method == "POST" and path.endswith("/events"):
            assert body is not None
            conversation_id = path.split("/")[3]
            self.events.setdefault(conversation_id, []).append(
                json.loads(json.dumps(body))
            )
            return {"accepted": True}
        if method == "POST" and path.endswith("/run"):
            return {"started": True}
        raise AssertionError(f"unexpected API call: {method} {path} {body}")


class MainApiPathTests(unittest.TestCase):
    """Drive real main() argv paths through the patched api seam.

    The ledger is redirected to a temp directory per test via the
    OPENHANDS_DISPATCH_LEDGER_DIR override (same seam as test_spawn.py) and
    all fixture conversation ids are UUIDs because ledger files are keyed by
    conversation UUID.
    """

    PARENT_ID = MAIN_PARENT_ID
    CHILD_ID = MAIN_CHILD_ID
    DISPATCH_ID = MAIN_DISPATCH_ID

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.prev_ledger_dir = os.environ.get("OPENHANDS_DISPATCH_LEDGER_DIR")
        os.environ["OPENHANDS_DISPATCH_LEDGER_DIR"] = os.path.join(
            self.tmp.name, "ledger"
        )

    def tearDown(self) -> None:
        if self.prev_ledger_dir is None:
            os.environ.pop("OPENHANDS_DISPATCH_LEDGER_DIR", None)
        else:
            os.environ["OPENHANDS_DISPATCH_LEDGER_DIR"] = self.prev_ledger_dir
        self.tmp.cleanup()

    def child(self, status="finished", **overrides):
        child = {
            "id": self.CHILD_ID,
            "parent_conversation_id": self.PARENT_ID,
            "execution_status": status,
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

    def report(self, include_identity=True, ticket="#24"):
        lines = ["engineering:report"]
        if include_identity:
            lines.extend(
                [
                    "dispatch-id: dispatch-1",
                    f"child-conversation-id: {self.CHILD_ID}",
                    "department: delivery",
                    f"ticket: {ticket}",
                ]
            )
        lines.extend(
            [
                "hop: done",
                "receipts: delivery implement=pass",
                "suggested next: 分发 acceptance #24",
            ]
        )
        return "\n".join(lines)

    def run_main(self, api, args, prompt):
        original_api = transport.api
        original_argv = sys.argv
        output = io.StringIO()
        try:
            transport.api = api
            with tempfile.TemporaryDirectory() as raw:
                prompt_path = Path(raw) / "prompt.txt"
                prompt_path.write_text(prompt, encoding="utf-8")
                sys.argv = ["spawn.py", *args, "--prompt-file", str(prompt_path)]
                with contextlib.redirect_stdout(output):
                    spawn.main()
        finally:
            transport.api = original_api
            sys.argv = original_argv
        # main() prints transport receipts before the final report; the
        # report is the last JSON object on stdout.
        text = output.getvalue().strip()
        decoder = json.JSONDecoder()
        idx = 0
        receipt = None
        while idx < len(text):
            while idx < len(text) and text[idx] in " \t\r\n":
                idx += 1
            receipt, idx = decoder.raw_decode(text, idx)
        return receipt

    def test_dispatch_verifies_and_returns_persisted_correlation(self) -> None:
        api = CanvasApi()
        receipt = self.run_main(
            api,
            [
                "--mode",
                "dispatch",
                "--this-id",
                self.PARENT_ID,
                "--profile-id",
                "123e4567-e89b-12d3-a456-426614174000",
                "--department",
                "delivery",
                "--ticket",
                "#24",
                "--dispatch-id",
                self.DISPATCH_ID,
                "--request-id",
                "req-dispatch-001",
            ],
            "deliver issue 24",
        )
        child = api.conversations[receipt["child_conversation_id"]]
        self.assertEqual(receipt["dispatch_id"], self.DISPATCH_ID)
        self.assertEqual(receipt["department"], "delivery")
        self.assertEqual(receipt["ticket"], "#24")
        self.assertEqual(child["parent_conversation_id"], self.PARENT_ID)
        self.assertEqual(child["tags"]["dispatch_id"], self.DISPATCH_ID)

    def test_dispatch_rejects_unpersisted_correlation(self) -> None:
        api = CanvasApi()
        api.dispatch_tag_override = {"ticket": "#23"}
        with self.assertRaisesRegex(
            SystemExit, "persisted dispatch metadata mismatch: ticket"
        ):
            self.run_main(
                api,
                [
                    "--mode",
                    "dispatch",
                    "--this-id",
                    self.PARENT_ID,
                    "--profile-id",
                    "123e4567-e89b-12d3-a456-426614174000",
                    "--department",
                    "delivery",
                    "--ticket",
                    "#24",
                    "--dispatch-id",
                    self.DISPATCH_ID,
                    "--request-id",
                    "req-dispatch-001",
                ],
                "deliver issue 24",
            )

    def test_notify_validates_exact_and_legacy_correlation(self) -> None:
        api = CanvasApi()
        api.conversations[self.CHILD_ID] = self.child()
        exact_receipt = self.run_main(
            api,
            ["--mode", "notify", "--this-id", self.CHILD_ID],
            self.report(),
        )
        self.assertEqual(exact_receipt["correlation"], "exact")
        self.assertTrue(exact_receipt["completion_eligible"])

        legacy_receipt = self.run_main(
            api,
            [
                "--mode",
                "notify",
                "--this-id",
                self.CHILD_ID,
                "--allow-legacy-report",
            ],
            self.report(include_identity=False),
        )
        self.assertEqual(legacy_receipt["correlation"], "legacy-unverified")
        self.assertFalse(legacy_receipt["completion_eligible"])
        legacy_event = [call for call in api.calls if call[1].endswith("/events")][-1]
        posted_text = legacy_event[2]["content"][0]["text"]
        self.assertIn("correlation: legacy-unverified", posted_text)
        self.assertIn("completion-eligible: false", posted_text)

    def test_notify_rejects_stale_incomplete_and_planning_callers(self) -> None:
        for report in (
            self.report(ticket="#23"),
            "engineering:report\nhop: done\nreceipts: delivery implement=pass",
        ):
            api = CanvasApi()
            api.conversations[self.CHILD_ID] = self.child()
            with self.subTest(report=report), self.assertRaises(SystemExit):
                self.run_main(
                    api,
                    ["--mode", "notify", "--this-id", self.CHILD_ID],
                    report,
                )
            event_calls = [call for call in api.calls if call[1].endswith("/events")]
            self.assertEqual(event_calls, [])

        # F1 on the main() path: a planning caller is refused before any
        # POST — spawn refuses a notify whose own conversation lacks a
        # parent_conversation_id, which planning windows never carry.
        api = CanvasApi()
        planning_child = self.child()
        planning_child["tags"]["department"] = "planning"
        del planning_child["parent_conversation_id"]
        api.conversations[self.CHILD_ID] = planning_child
        with self.assertRaisesRegex(SystemExit, "Planning must not notify"):
            self.run_main(
                api,
                ["--mode", "notify", "--this-id", self.CHILD_ID],
                self.report(),
            )
        event_calls = [call for call in api.calls if call[1].endswith("/events")]
        self.assertEqual(event_calls, [])

    def test_terminal_and_non_terminal_resume_post_single_role_form_event(self) -> None:
        # Adopted new-main semantics: both terminal and non-terminal
        # resumable targets continue via one role-form event with run=true.
        cases = [("finished", "req-resume-001"), ("paused", "req-resume-002")]
        for status, request_id in cases:
            api = CanvasApi()
            api.conversations[self.CHILD_ID] = self.child(status)
            # The binding comes from the original accepted dispatch entry;
            # the resume itself uses a fresh request id.
            spawn.record_ledger(
                self.PARENT_ID,
                "req-dispatch-001",
                spawn.ledger_entry(
                    operation="dispatch",
                    request_id="req-dispatch-001",
                    ticket="#24",
                    department="delivery",
                    parent_id=self.PARENT_ID,
                    status="accepted",
                    evidence="seeded dispatch binding",
                    child_id=self.CHILD_ID,
                    working_dir="C:/repo",
                ),
            )
            receipt = self.run_main(
                api,
                [
                    "--mode",
                    "resume",
                    "--this-id",
                    self.PARENT_ID,
                    "--target-id",
                    self.CHILD_ID,
                    "--request-id",
                    request_id,
                    "--ticket",
                    "#24",
                ],
                "retry finalization only",
            )
            events = [call for call in api.calls if call[1].endswith("/events")]
            run_calls = [call for call in api.calls if call[1].endswith("/run")]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0][2]["run"], True)
            self.assertEqual(events[0][2]["role"], "user")
            self.assertEqual(run_calls, [])
            self.assertEqual(receipt["receipt"], "accepted")
            self.assertEqual(receipt["resume_behavior"], "message-with-run")

    def test_resume_rejection_does_not_mutate_target(self) -> None:
        api = CanvasApi()
        api.conversations[self.CHILD_ID] = self.child(
            parent_conversation_id="other"
        )
        with self.assertRaisesRegex(SystemExit, "not a direct child"):
            self.run_main(
                api,
                [
                    "--mode",
                    "resume",
                    "--this-id",
                    self.PARENT_ID,
                    "--target-id",
                    self.CHILD_ID,
                    "--request-id",
                    "req-resume-010",
                    "--ticket",
                    "#24",
                ],
                "retry finalization only",
            )


class SeamImportSurfaceTests(unittest.TestCase):
    """Pin the split-module import surface (ticket #25 seam contract).

    Ticket #53 may modify each seam independently; these assertions keep the
    package layout and the spawn facade re-exports stable so callers and
    fixtures keep working across seam-internal changes.
    """

    def test_seam_modules_import(self) -> None:
        import canvas_sessions  # package init
        from canvas_sessions import dispatch, identity, ledger, notify, resume, transport

        self.assertTrue(hasattr(canvas_sessions, "__path__"))
        for seam in (transport, identity, ledger, dispatch, resume, notify):
            self.assertTrue(hasattr(seam, "__name__"), seam)

    def test_transport_holds_the_only_http_entry_points(self) -> None:
        from canvas_sessions import transport

        for name in ("session_key", "api", "get_conversation", "github_binding"):
            self.assertTrue(callable(getattr(transport, name)), name)
        self.assertEqual(transport.EVENT_POST_TIMEOUT, 180)

    def test_spawn_facade_reexports_former_public_surface(self) -> None:
        surface = (
            "BASE",
            "KEY_PATH",
            "UI",
            "SECRET_NAME",
            "GITHUB_CONSUMER",
            "EVENT_POST_TIMEOUT",
            "session_key",
            "api",
            "github_binding",
            "probe_secret_source",
            "binding_status",
            "get_conversation",
            "maybe_run",
            "ensure_child",
            "WT_SEGMENT",
            "SIBLING_TREE",
            "TICKET_FORM",
            "REQUEST_FORM",
            "TERMINAL_STATES",
            "AUTHORIZED_DEPARTMENTS",
            "DEPARTMENTS",
            "working_dir_of",
            "norm_path",
            "refuse_path",
            "canvas_tags",
            "status_of",
            "search_items",
            "search_running",
            "validate_profile_id",
            "normalize_ticket",
            "normalize_request_id",
            "request_identity",
            "dispatch_request_child_id",
            "imported_from_cwd",
            "cwd_match_paths",
            "is_workspace_hit",
            "updated_key",
            "pick_workspace_id",
            "resolve_this",
            "prompt_digest",
            "ledger_dir",
            "ledger_path",
            "load_ledger",
            "save_ledger",
            "record_ledger",
            "ledger_entry",
            "make_receipt",
            "emit_receipt",
            "http_op",
            "refuse_duplicate_dispatch",
            "reconcile_event_marker",
            "refuse_duplicate_from_ledger",
            "verify_request_payload",
            "reconciled_receipt",
            "reconcile_dispatch_entry",
            "resume_rejection",
            "reconcile_resume_entry",
            "bound_department_prompt",
            "conversation_body",
            "run_dispatch",
            "validate_persisted_dispatch",
            "post_message",
            "validate_resume",
            "run_resume",
            "REPORT_PREFIX",
            "REPORT_HOPS",
            "report_fields",
            "validate_report",
            "event_payload",
            "send_event",
            "event_text_blob",
            "target_event_texts",
            "event_marker",
            "run_notify",
            "HTTPError",
            "URLError",
            "main",
        )
        for name in surface:
            with self.subTest(name=name):
                self.assertTrue(hasattr(spawn, name), name)


if __name__ == "__main__":
    unittest.main()
