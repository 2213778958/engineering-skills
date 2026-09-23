#!/usr/bin/env python3
"""Offline unit tests for the engineering-watch classifier.

No live API: probe rows and parent event texts are injected fakes.
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "openhands-watch" / "scripts"))

from watch import classify
from watch_engineering import (
    build_snapshot,
    correlated_report,
    engineering_classify,
    engineering_exit_code,
    finalization_failed,
    is_correlated_report,
    request_identity,
    rollup,
)

NOW = datetime(2026, 9, 23, 4, 0, tzinfo=timezone.utc)
PARENT = "22222222-2222-2222-2222-222222222222"
CHILD = "11111111-1111-1111-1111-111111111111"
OTHER = "33333333-3333-3333-3333-333333333333"
DEPARTMENT = "delivery"
TICKET = "#23"
REQUEST_ID = "abcdef0123456789"

REPORT = (
    "engineering:report\n"
    f"department: {DEPARTMENT}\n"
    f"ticket: {TICKET}\n"
    "hop: done\n"
    f"request: {REQUEST_ID}\n"
    "receipts: implement=pass\n"
)

FINALIZATION_FAILED_TEXT = (
    "done except finalization failed: push failed, notify failed, "
    "PROCESS.md untouched"
)


def conv(**over: object) -> dict:
    row = {
        "id": CHILD,
        "execution_status": "running",
        "updated_at": "2026-09-23T03:59:00Z",
        "created_at": "2026-09-23T03:00:00Z",
        "tags": {"clientsource": "agentcanvas"},
        "parent_conversation_id": PARENT,
    }
    row.update(over)
    return row


def running_row() -> dict:
    return classify(conv(), "2026-09-23T03:59:30Z", NOW, 600, CHILD)


def terminal_row(final: str | None = None) -> dict:
    row = classify(
        conv(execution_status="finished"),
        "2026-09-23T03:10:00Z",
        NOW,
        600,
        CHILD,
    )
    if final is not None:
        row["final_response"] = final
    return row


class IdentityTests(unittest.TestCase):
    def test_identity_matches_spawn(self) -> None:
        self.assertEqual(
            request_identity(PARENT, DEPARTMENT, TICKET, REQUEST_ID),
            f"dispatch:{PARENT}:{DEPARTMENT}:{TICKET}:{REQUEST_ID}",
        )

    def test_correlated_report_matches(self) -> None:
        self.assertTrue(
            is_correlated_report(REPORT, PARENT, DEPARTMENT, TICKET, REQUEST_ID)
        )
        self.assertEqual(
            correlated_report([REPORT], PARENT, DEPARTMENT, TICKET, REQUEST_ID),
            REPORT,
        )

    def test_uncorrelated_report_rejected(self) -> None:
        wrong_request = REPORT.replace(REQUEST_ID, "ffffffffffffffff")
        wrong_department = REPORT.replace(DEPARTMENT, "acceptance")
        wrong_ticket = REPORT.replace(TICKET, "#24")
        not_report = REPORT.replace("engineering:report", "hop note", 1)
        for text in (wrong_request, wrong_department, wrong_ticket, not_report):
            self.assertIsNone(
                correlated_report([text], PARENT, DEPARTMENT, TICKET, REQUEST_ID)
            )


class AliveTests(unittest.TestCase):
    def test_alive(self) -> None:
        out = engineering_classify(
            running_row(), [REPORT], PARENT, DEPARTMENT, TICKET, REQUEST_ID
        )
        self.assertEqual(out["engineering_status"], "alive")
        self.assertIsNone(out["report"])

    def test_alive_long_wait_without_stall_is_alive(self) -> None:
        old = (NOW - timedelta(seconds=599)).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = classify(conv(), old, NOW, 600, CHILD)
        out = engineering_classify(row, [], PARENT, DEPARTMENT, TICKET, REQUEST_ID)
        self.assertEqual(out["engineering_status"], "alive")


class HungTests(unittest.TestCase):
    def test_stall_fallback_is_hung(self) -> None:
        old = (NOW - timedelta(seconds=601)).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = classify(conv(), old, NOW, 600, CHILD)
        out = engineering_classify(row, [], PARENT, DEPARTMENT, TICKET, REQUEST_ID)
        self.assertEqual(out["engineering_status"], "hung")

    def test_stuck_is_hung(self) -> None:
        row = classify(conv(execution_status="stuck"), None, NOW, 600, CHILD)
        out = engineering_classify(row, [], PARENT, DEPARTMENT, TICKET, REQUEST_ID)
        self.assertEqual(out["engineering_status"], "hung")

    def test_not_found_is_hung(self) -> None:
        row = classify(None, None, NOW, 600, CHILD)
        out = engineering_classify(row, [], PARENT, DEPARTMENT, TICKET, REQUEST_ID)
        self.assertEqual(out["engineering_status"], "hung")


class NotifiedTests(unittest.TestCase):
    def test_terminal_notified(self) -> None:
        out = engineering_classify(
            terminal_row(), [REPORT], PARENT, DEPARTMENT, TICKET, REQUEST_ID
        )
        self.assertEqual(out["engineering_status"], "terminal + notified")
        self.assertEqual(out["report"]["request"], REQUEST_ID)
        self.assertEqual(out["report"]["department"], DEPARTMENT)
        self.assertEqual(out["report"]["ticket"], TICKET)

    def test_other_child_report_in_parent_stream_does_not_correlate(self) -> None:
        sibling_report = REPORT.replace(REQUEST_ID, "ffffffffffffffff")
        out = engineering_classify(
            terminal_row(), [sibling_report], PARENT, DEPARTMENT, TICKET, REQUEST_ID
        )
        self.assertEqual(out["engineering_status"], "terminal + missing-notify")
        self.assertIsNone(out["report"])


class MissingNotifyTests(unittest.TestCase):
    def test_terminal_without_report(self) -> None:
        out = engineering_classify(
            terminal_row("all done"), [], PARENT, DEPARTMENT, TICKET, REQUEST_ID
        )
        self.assertEqual(out["engineering_status"], "terminal + missing-notify")

    def test_unrelated_report_present(self) -> None:
        other_report = REPORT.replace(TICKET, "#99").replace(
            REQUEST_ID, "0123456789abcdef"
        )
        out = engineering_classify(
            terminal_row("all done"),
            [other_report],
            PARENT,
            DEPARTMENT,
            TICKET,
            REQUEST_ID,
        )
        self.assertEqual(out["engineering_status"], "terminal + missing-notify")


class FinalizationFailedTests(unittest.TestCase):
    def test_finalization_failed_not_success(self) -> None:
        out = engineering_classify(
            terminal_row(FINALIZATION_FAILED_TEXT),
            [],
            PARENT,
            DEPARTMENT,
            TICKET,
            REQUEST_ID,
        )
        self.assertEqual(out["engineering_status"], "terminal + finalization-failed")

    def test_finalization_failed_even_with_unrelated_report(self) -> None:
        other_report = REPORT.replace(REQUEST_ID, "ffffffffffffffff")
        out = engineering_classify(
            terminal_row(FINALIZATION_FAILED_TEXT),
            [other_report],
            PARENT,
            DEPARTMENT,
            TICKET,
            REQUEST_ID,
        )
        self.assertEqual(out["engineering_status"], "terminal + finalization-failed")

    def test_finalization_marker_detection(self) -> None:
        self.assertTrue(finalization_failed("收尾失败: notify fail"))
        self.assertFalse(finalization_failed("pushed and notified ok"))

    def test_long_final_response_truncated(self) -> None:
        out = engineering_classify(terminal_row("x" * 500), [], PARENT)
        self.assertLessEqual(len(out["final_response"]), 161)
        self.assertTrue(out["final_response"].endswith("…"))


class RollupTests(unittest.TestCase):
    def test_rollup_and_exit(self) -> None:
        notified = {"engineering_status": "terminal + notified"}
        alive = {"engineering_status": "alive"}
        hung = {"engineering_status": "hung"}
        gap = {"engineering_status": "terminal + missing-notify"}
        fin = {"engineering_status": "terminal + finalization-failed"}
        self.assertEqual(rollup([notified, notified]), "notified")
        self.assertEqual(rollup([notified, alive]), "alive")
        self.assertEqual(rollup([notified, hung]), "hung")
        self.assertEqual(rollup([notified, gap]), "gap")
        self.assertEqual(rollup([notified, fin]), "gap")
        self.assertEqual(engineering_exit_code("notified"), 0)
        self.assertEqual(engineering_exit_code("alive"), 2)
        self.assertEqual(engineering_exit_code("hung"), 2)
        self.assertEqual(engineering_exit_code("gap"), 3)


class SnapshotTests(unittest.TestCase):
    def test_snapshot_notified(self) -> None:
        payload = build_snapshot(
            [CHILD],
            PARENT,
            600,
            DEPARTMENT,
            TICKET,
            REQUEST_ID,
            now=NOW,
            event_reader=lambda pid: [REPORT] if pid == PARENT else [],
            prober=lambda cid, stall, clock: terminal_row(),
        )
        self.assertEqual(payload["verdict"], "notified")
        self.assertEqual(
            payload["children"][0]["engineering_status"], "terminal + notified"
        )

    def test_snapshot_gap_and_no_mutation(self) -> None:
        row = terminal_row(FINALIZATION_FAILED_TEXT)
        before = dict(row)
        payload = build_snapshot(
            [CHILD],
            PARENT,
            600,
            DEPARTMENT,
            TICKET,
            REQUEST_ID,
            now=NOW,
            event_reader=lambda pid: [],
            prober=lambda cid, stall, clock: row,
        )
        self.assertEqual(payload["verdict"], "gap")
        self.assertEqual(
            payload["children"][0]["engineering_status"],
            "terminal + finalization-failed",
        )
        self.assertEqual(row, before)

    def test_snapshot_alive(self) -> None:
        payload = build_snapshot(
            [CHILD],
            PARENT,
            600,
            DEPARTMENT,
            TICKET,
            REQUEST_ID,
            now=NOW,
            event_reader=lambda pid: [],
            prober=lambda cid, stall, clock: running_row(),
        )
        self.assertEqual(payload["verdict"], "alive")
        self.assertEqual(payload["children"][0]["engineering_status"], "alive")

    def test_classifier_does_not_call_mutating_primitives(self) -> None:
        calls: list[str] = []

        def fake_prober(cid: str, stall: int, clock: datetime) -> dict:
            calls.append(cid)
            return terminal_row()

        build_snapshot(
            [CHILD],
            PARENT,
            600,
            DEPARTMENT,
            TICKET,
            REQUEST_ID,
            now=NOW,
            event_reader=lambda pid: [REPORT],
            prober=fake_prober,
        )
        self.assertEqual(calls, [CHILD])


if __name__ == "__main__":
    unittest.main()
