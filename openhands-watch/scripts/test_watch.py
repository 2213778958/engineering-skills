#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from watch import (
    attach_task_facts,
    classify,
    common_parent,
    exit_code,
    find_dispatch_entry,
    load_parent_ledger,
    notify_state,
    parse_ids,
    rollup,
)

NOW = datetime(2026, 9, 19, 3, 20, tzinfo=timezone.utc)
CID = "11111111-1111-1111-1111-111111111111"
PARENT = "22222222-2222-2222-2222-222222222222"
OTHER = "33333333-3333-3333-3333-333333333333"


def conv(**over: object) -> dict:
    row = {
        "id": CID,
        "execution_status": "running",
        "updated_at": "2026-09-19T03:19:00Z",
        "created_at": "2026-09-19T03:00:00Z",
        "tags": {"clientsource": "agentcanvas"},
        "parent_conversation_id": "22222222-2222-2222-2222-222222222222",
    }
    row.update(over)
    return row


class ClassifyTests(unittest.TestCase):
    def test_finished(self) -> None:
        row = classify(conv(execution_status="finished"), "2026-09-19T03:10:00Z", NOW, 600, CID)
        self.assertEqual(row["verdict"], "terminal")
        self.assertEqual(row["reason"], "finished")

    def test_error(self) -> None:
        row = classify(conv(execution_status="error"), None, NOW, 600, CID)
        self.assertEqual(row["verdict"], "terminal")
        self.assertEqual(row["reason"], "error")

    def test_stuck(self) -> None:
        row = classify(conv(execution_status="stuck"), "2026-09-19T03:19:00Z", NOW, 600, CID)
        self.assertEqual(row["verdict"], "hung")
        self.assertEqual(row["reason"], "stuck")

    def test_waiting_for_confirmation(self) -> None:
        row = classify(
            conv(execution_status="waiting_for_confirmation"),
            "2026-09-19T03:19:00Z",
            NOW,
            600,
            CID,
        )
        self.assertEqual((row["verdict"], row["reason"]), ("hung", "waiting_for_confirmation"))

    def test_alive(self) -> None:
        row = classify(conv(), "2026-09-19T03:19:30Z", NOW, 600, CID)
        self.assertEqual(row["verdict"], "alive")
        self.assertEqual(row["age_sec"], 30)

    def test_stall(self) -> None:
        old = (NOW - timedelta(seconds=601)).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = classify(conv(), old, NOW, 600, CID)
        self.assertEqual((row["verdict"], row["reason"]), ("hung", "stall"))

    def test_missing_clientsource_while_running(self) -> None:
        row = classify(conv(tags={}), "2026-09-19T03:19:30Z", NOW, 600, CID)
        self.assertEqual((row["verdict"], row["reason"]), ("hung", "missing-clientsource"))

    def test_finished_without_clientsource_is_terminal(self) -> None:
        row = classify(
            conv(execution_status="finished", tags={}),
            "2026-09-19T03:10:00Z",
            NOW,
            600,
            CID,
        )
        self.assertEqual(row["verdict"], "terminal")

    def test_not_found(self) -> None:
        row = classify(None, None, NOW, 600, CID)
        self.assertEqual((row["verdict"], row["reason"]), ("hung", "not-found"))

    def test_naive_event_timestamp_is_local(self) -> None:
        local = datetime.now().astimezone().tzinfo
        naive = "2026-09-19T03:19:00"
        expected = int((NOW - datetime.fromisoformat(naive).replace(tzinfo=local).astimezone(timezone.utc)).total_seconds())
        row = classify(conv(), naive, NOW, 10**9, CID)
        self.assertEqual(row["verdict"], "alive")
        self.assertEqual(row["age_sec"], max(0, expected))

    def test_rollup_and_exit(self) -> None:
        hung = {"verdict": "hung", "reason": "stall"}
        alive = {"verdict": "alive", "reason": "running"}
        done = {"verdict": "terminal", "reason": "finished"}
        bad = {"verdict": "terminal", "reason": "error"}
        self.assertEqual(rollup([done, alive]), "alive")
        self.assertEqual(rollup([done, hung]), "hung")
        self.assertEqual(rollup([done, done]), "terminal")
        self.assertEqual(exit_code("hung", [hung]), 2)
        self.assertEqual(exit_code("terminal", [done]), 0)
        self.assertEqual(exit_code("terminal", [bad]), 3)

    def test_parse_ids(self) -> None:
        self.assertEqual(
            parse_ids(["a,b", "b", "c"]),
            ["a", "b", "c"],
        )


def dispatch_entry(**over: object) -> dict:
    entry = {
        "operation": "dispatch",
        "request_id": "req-1",
        "ticket": "#26",
        "department": "delivery",
        "parent_id": PARENT,
        "child_id": CID,
        "status": "accepted",
        "recorded_at": "2026-09-19T03:00:00+00:00",
    }
    entry.update(over)
    return entry


def notify_entry(**over: object) -> dict:
    entry = {
        "operation": "notify",
        "request_id": "notify-1",
        "ticket": "#26",
        "department": "",
        "parent_id": PARENT,
        "target_id": PARENT,
        "status": "accepted",
        "recorded_at": "2026-09-19T03:10:00+00:00",
    }
    entry.update(over)
    return entry


class LedgerBase(unittest.TestCase):
    """Isolate ledger reads behind OPENHANDS_DISPATCH_LEDGER_DIR."""

    def setUp(self) -> None:
        self.prev_dir = os.environ.get("OPENHANDS_DISPATCH_LEDGER_DIR")
        self.ledger_dir = tempfile.mkdtemp(prefix="watch-ledger-")
        os.environ["OPENHANDS_DISPATCH_LEDGER_DIR"] = self.ledger_dir

    def tearDown(self) -> None:
        if self.prev_dir is None:
            os.environ.pop("OPENHANDS_DISPATCH_LEDGER_DIR", None)
        else:
            os.environ["OPENHANDS_DISPATCH_LEDGER_DIR"] = self.prev_dir
        shutil.rmtree(self.ledger_dir, ignore_errors=True)

    def write_ledger(self, payload: object, parent: str = PARENT) -> Path:
        path = Path(self.ledger_dir) / f"{parent}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


class LoadLedgerTests(LedgerBase):
    def test_reads_dispatch_ledger(self) -> None:
        self.write_ledger({"req-1": dispatch_entry()})
        ledger = load_parent_ledger(PARENT)
        self.assertEqual(ledger, {"req-1": dispatch_entry()})

    def test_missing_ledger_file_is_empty(self) -> None:
        self.assertEqual(load_parent_ledger(PARENT), {})

    def test_corrupt_ledger_degrades_to_none(self) -> None:
        bad = Path(self.ledger_dir, f"{PARENT}.json")
        bad.write_text("{not json", encoding="utf-8")
        self.assertIsNone(load_parent_ledger(PARENT))

    def test_non_uuid_parent_degrades_to_none(self) -> None:
        self.assertIsNone(load_parent_ledger("../escape"))
        self.assertIsNone(load_parent_ledger(""))

    def test_watch_never_calls_ledger_writers(self) -> None:
        import inspect

        import watch

        source = inspect.getsource(watch)
        self.assertNotIn("save_ledger(", source)
        self.assertNotIn("record_ledger(", source)


class FindDispatchEntryTests(unittest.TestCase):
    def test_matches_by_child_id(self) -> None:
        entry, conflict = find_dispatch_entry({"req-1": dispatch_entry()}, CID)
        self.assertIsNone(conflict)
        self.assertEqual(entry, dispatch_entry())

    def test_ignores_other_operations_and_children(self) -> None:
        ledger = {
            "notify-1": notify_entry(child_id=CID),
            "req-2": dispatch_entry(child_id=OTHER),
        }
        entry, conflict = find_dispatch_entry(ledger, CID)
        self.assertIsNone(entry)
        self.assertEqual(conflict, "no-dispatch-entry")

    def test_replays_with_same_identity_are_one_entry(self) -> None:
        ledger = {
            "req-1": dispatch_entry(),
            "req-1b": dispatch_entry(recorded_at="2026-09-19T03:01:00+00:00"),
        }
        entry, conflict = find_dispatch_entry(ledger, CID)
        self.assertIsNone(conflict)
        self.assertEqual(entry, dispatch_entry())

    def test_conflicting_dispatch_entries(self) -> None:
        ledger = {
            "req-1": dispatch_entry(ticket="#26"),
            "req-2": dispatch_entry(ticket="#27", request_id="req-2"),
        }
        entry, conflict = find_dispatch_entry(ledger, CID)
        self.assertIsNone(entry)
        self.assertEqual(conflict, "conflicting-dispatch-entries")


class NotifyStateTests(unittest.TestCase):
    def test_notified(self) -> None:
        ledger = {"req-1": dispatch_entry(), "notify-1": notify_entry()}
        self.assertEqual(
            notify_state(ledger, dispatch_entry(), terminal=True), "notified"
        )

    def test_missing_notify(self) -> None:
        ledger = {"req-1": dispatch_entry()}
        self.assertEqual(
            notify_state(ledger, dispatch_entry(), terminal=True), "missing-notify"
        )

    def test_non_terminal_is_na(self) -> None:
        self.assertEqual(notify_state({}, dispatch_entry(), terminal=False), "n/a")

    def test_terminal_without_dispatch_entry_fails(self) -> None:
        self.assertEqual(notify_state({}, None, terminal=True), "finalization-failed")

    def test_notify_ticket_matching_no_dispatch_ticket_fails(self) -> None:
        ledger = {
            "req-1": dispatch_entry(ticket="#26"),
            "notify-1": notify_entry(ticket="#99"),
        }
        self.assertEqual(
            notify_state(ledger, dispatch_entry(), terminal=True),
            "finalization-failed",
        )


class CommonParentTests(unittest.TestCase):
    def test_single_common_parent(self) -> None:
        rows = [
            {"parent_conversation_id": PARENT},
            {"parent_conversation_id": PARENT},
        ]
        self.assertEqual(common_parent(rows), PARENT)

    def test_missing_or_divergent_parents(self) -> None:
        self.assertEqual(common_parent([]), "")
        self.assertEqual(common_parent([{"parent_conversation_id": None}]), "")
        self.assertEqual(
            common_parent(
                [
                    {"parent_conversation_id": PARENT},
                    {"parent_conversation_id": OTHER},
                ]
            ),
            "",
        )


class AttachTaskFactsTests(LedgerBase):
    def row(self, verdict: str = "terminal", **over: object) -> dict:
        base = {
            "id": CID,
            "verdict": verdict,
            "reason": "finished" if verdict == "terminal" else "running",
            "status": "finished" if verdict == "terminal" else "running",
            "parent_conversation_id": PARENT,
        }
        base.update(over)
        return base

    def test_notified_terminal_child(self) -> None:
        self.write_ledger({"req-1": dispatch_entry(), "notify-1": notify_entry()})
        rows = attach_task_facts([self.row()])
        task = rows[0]["task"]
        self.assertEqual(task["notify"], "notified")
        self.assertEqual(task["reason"], "")
        self.assertEqual(task["ticket"], "#26")
        self.assertEqual(task["department"], "delivery")
        self.assertEqual(task["request_id"], "req-1")
        self.assertEqual(task["dispatch_status"], "accepted")
        self.assertEqual(task["recorded_at"], "2026-09-19T03:00:00+00:00")
        self.assertEqual(rows[0]["verdict"], "terminal")

    def test_missing_notify_terminal_child(self) -> None:
        self.write_ledger({"req-1": dispatch_entry()})
        rows = attach_task_facts([self.row()])
        task = rows[0]["task"]
        self.assertEqual(task["notify"], "missing-notify")
        self.assertEqual(task["ticket"], "#26")

    def test_conflicting_entries_fail_finalization(self) -> None:
        self.write_ledger(
            {
                "req-1": dispatch_entry(ticket="#26"),
                "req-2": dispatch_entry(ticket="#27", request_id="req-2"),
            }
        )
        rows = attach_task_facts([self.row()])
        task = rows[0]["task"]
        self.assertEqual(task["notify"], "finalization-failed")
        self.assertEqual(task["reason"], "conflicting-dispatch-entries")
        self.assertIsNone(task["ticket"])

    def test_unreadable_ledger_degrades_but_verdict_survives(self) -> None:
        bad = Path(self.ledger_dir, f"{PARENT}.json")
        bad.write_text("{oops", encoding="utf-8")
        rows = attach_task_facts([self.row(), self.row(verdict="alive")])
        self.assertEqual(rows[0]["verdict"], "terminal")
        self.assertEqual(rows[0]["task"]["notify"], "finalization-failed")
        self.assertEqual(rows[0]["task"]["reason"], "ledger-unreadable")
        self.assertIsNone(rows[0]["task"]["ticket"])
        self.assertEqual(rows[1]["verdict"], "alive")
        self.assertEqual(rows[1]["task"]["notify"], "finalization-failed")

    def test_non_terminal_child_is_na(self) -> None:
        self.write_ledger({"req-1": dispatch_entry()})
        rows = attach_task_facts([self.row(verdict="alive")])
        task = rows[0]["task"]
        self.assertEqual(task["notify"], "n/a")
        self.assertEqual(task["ticket"], "#26")
        self.assertEqual(task["reason"], "")

    def test_ids_only_without_parent_is_unknown(self) -> None:
        rows = attach_task_facts(
            [
                self.row(parent_conversation_id=None),
                self.row(verdict="alive", parent_conversation_id=None),
            ]
        )
        self.assertEqual(rows[0]["task"]["notify"], "unknown")
        self.assertEqual(rows[0]["task"]["reason"], "parent-ledger-unavailable")
        self.assertIsNone(rows[0]["task"]["ticket"])
        self.assertEqual(rows[1]["task"]["notify"], "n/a")

    def test_explicit_parent_wins_and_empty_ledger_fails_terminal(self) -> None:
        rows = attach_task_facts([self.row()], parent_id=PARENT)
        task = rows[0]["task"]
        self.assertEqual(task["notify"], "finalization-failed")
        self.assertEqual(task["reason"], "no-dispatch-entry")

    def test_common_parent_resolved_from_rows(self) -> None:
        self.write_ledger(
            {"req-1": dispatch_entry(), "notify-1": notify_entry()}, parent=PARENT
        )
        rows = attach_task_facts([self.row(parent_conversation_id=PARENT)])
        self.assertEqual(rows[0]["task"]["notify"], "notified")


if __name__ == "__main__":
    unittest.main()
