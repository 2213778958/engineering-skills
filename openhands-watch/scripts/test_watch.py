#!/usr/bin/env python3
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from watch import classify, exit_code, parse_ids, rollup

NOW = datetime(2026, 9, 19, 3, 20, tzinfo=timezone.utc)
CID = "11111111-1111-1111-1111-111111111111"


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


if __name__ == "__main__":
    unittest.main()
