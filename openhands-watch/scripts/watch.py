#!/usr/bin/env python3
"""Watch Agent Canvas child conversations. Never print the API key. Never POST."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "openhands-sessions" / "scripts")
)
from canvas_sessions import ledger as sessions_ledger
from canvas_sessions import transport

BASE = transport.BASE
UI = transport.UI

TERMINAL_OK = frozenset({"finished"})
TERMINAL_BAD = frozenset({"error", "stopped"})
HUNG_STATUS = frozenset(
    {"stuck", "waiting_for_confirmation", "paused", "deleting"}
)
RESPONSE_CAP = 2000


def api(method: str, path: str, timeout: int = 60) -> object:
    return transport.api(method, path, timeout=timeout)


def get_conversation(cid: str) -> dict | None:
    return transport.get_conversation(cid)


def parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed.astimezone(timezone.utc)


def age_sec(stamp: datetime | None, now: datetime) -> int | None:
    if stamp is None:
        return None
    return max(0, int((now - stamp).total_seconds()))


def last_event_at(cid: str) -> str | None:
    qs = urlencode({"limit": 1, "sort_order": "TIMESTAMP_DESC"})
    try:
        payload = api("GET", f"/api/conversations/{cid}/events/search?{qs}")
    except SystemExit:
        return None
    if not isinstance(payload, dict):
        return None
    items = payload.get("items") or []
    if not items or not isinstance(items[0], dict):
        return None
    ts = items[0].get("timestamp")
    return ts if isinstance(ts, str) else None


def final_response(cid: str) -> str | None:
    try:
        payload = api("GET", f"/api/conversations/{cid}/agent_final_response")
    except SystemExit:
        return None
    if not isinstance(payload, dict):
        return None
    text = payload.get("response")
    if not isinstance(text, str) or not text:
        return None
    if len(text) > RESPONSE_CAP:
        return text[:RESPONSE_CAP] + "…"
    return text


def status_of(conv: dict) -> str:
    val = conv.get("execution_status")
    if isinstance(val, str) and val:
        return val
    return "unknown"


def tags_of(conv: dict) -> dict[str, str]:
    tags = conv.get("tags") if isinstance(conv.get("tags"), dict) else {}
    return {str(k): str(v) for k, v in tags.items() if k is not None and v is not None}


def classify(
    conv: dict | None,
    last_event: str | None,
    now: datetime,
    stall_sec: int,
    cid: str,
) -> dict[str, Any]:
    if conv is None:
        return {
            "id": cid,
            "verdict": "hung",
            "reason": "not-found",
            "status": "missing",
            "last_event_at": last_event,
            "updated_at": None,
            "age_sec": None,
            "tags": {},
            "parent_conversation_id": None,
            "url": f"{UI}/conversations/{cid}",
        }
    status = status_of(conv)
    tags = tags_of(conv)
    updated = conv.get("updated_at")
    if not isinstance(updated, str):
        updated = None
    heartbeat = (
        parse_ts(last_event) or parse_ts(updated) or parse_ts(conv.get("created_at"))
    )
    age = age_sec(heartbeat, now)
    row: dict[str, Any] = {
        "id": conv.get("id") or cid,
        "verdict": "alive",
        "reason": "running",
        "status": status,
        "last_event_at": last_event,
        "updated_at": updated,
        "age_sec": age,
        "tags": tags,
        "parent_conversation_id": conv.get("parent_conversation_id"),
        "url": f"{UI}/conversations/{cid}",
    }
    if status in TERMINAL_OK:
        row["verdict"] = "terminal"
        row["reason"] = "finished"
        return row
    if status in TERMINAL_BAD:
        row["verdict"] = "terminal"
        row["reason"] = status
        return row
    if status in HUNG_STATUS:
        row["verdict"] = "hung"
        row["reason"] = status
        return row
    if tags.get("clientsource") != "agentcanvas":
        row["verdict"] = "hung"
        row["reason"] = "missing-clientsource"
        return row
    if age is None or age >= stall_sec:
        row["verdict"] = "hung"
        row["reason"] = "stall"
        return row
    row["reason"] = status or "running"
    return row


def rollup(children: list[dict[str, Any]]) -> str:
    if any(row["verdict"] == "hung" for row in children):
        return "hung"
    if any(row["verdict"] == "alive" for row in children):
        return "alive"
    return "terminal"


def exit_code(verdict: str, children: list[dict[str, Any]]) -> int:
    if verdict == "hung":
        return 2
    if any(
        row.get("reason") not in {"finished"} and row["verdict"] == "terminal"
        for row in children
    ):
        return 3
    if verdict == "terminal":
        return 0
    return 0


def parse_ids(raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for chunk in raw:
        for part in chunk.split(","):
            cid = part.strip()
            if cid and cid not in seen:
                seen.add(cid)
                out.append(cid)
    return out


NOTIFY_NOTIFIED = "notified"
NOTIFY_MISSING = "missing-notify"
NOTIFY_FAILED = "finalization-failed"
NOTIFY_NA = "n/a"
NOTIFY_UNKNOWN = "unknown"


def load_parent_ledger(parent_id: str) -> dict | None:
    """Read one parent's dispatch ledger, degrading to None when unreadable.

    Unlike the sessions loader, which fails closed, watch is a read-only
    observer: an unreadable, corrupt, or non-UUID-keyed ledger must never
    stop the liveness verdict, so every failure mode yields None.

    Args:
        parent_id: Parent conversation UUID (ledger key).

    Returns:
        Mapping of request id to ledger entry, {} when the ledger file does
        not exist yet, or None when the ledger cannot be read.
    """
    if not parent_id:
        return None
    try:
        return sessions_ledger.load_ledger(parent_id)
    except (SystemExit, OSError, ValueError):
        return None


def find_dispatch_entry(
    ledger: dict, child_id: str
) -> tuple[dict | None, str | None]:
    """Match one child's dispatch entry in a readable parent ledger.

    Args:
        ledger: Mapping of request id to ledger entry.
        child_id: Child conversation id matched against entry ``child_id``.

    Returns:
        Tuple of the dispatch entry (first one when repeated attempts share
        one identity) and a contradiction reason. The entry is None when no
        entry matches or when the ledger holds conflicting dispatch entries
        for the child.
    """
    entries = [
        entry
        for entry in ledger.values()
        if isinstance(entry, dict)
        and entry.get("operation") == "dispatch"
        and str(entry.get("child_id") or "") == child_id
    ]
    if not entries:
        return None, "no-dispatch-entry"
    signatures = {
        (
            str(entry.get("ticket") or ""),
            str(entry.get("department") or ""),
            str(entry.get("request_id") or ""),
        )
        for entry in entries
    }
    if len(signatures) > 1:
        return None, "conflicting-dispatch-entries"
    return entries[0], None


def ledger_notify_conflict(ledger: dict) -> bool:
    """Detect notify entries that reference a ticket never dispatched.

    Args:
        ledger: Mapping of request id to ledger entry.

    Returns:
        True when any notify entry's ticket matches no dispatch entry in the
        same ledger, which contradicts the child->parent hop protocol.
    """
    tickets = {
        str(entry.get("ticket") or "")
        for entry in ledger.values()
        if isinstance(entry, dict) and entry.get("operation") == "dispatch"
    }
    return any(
        isinstance(entry, dict)
        and entry.get("operation") == "notify"
        and str(entry.get("ticket") or "") not in tickets
        for entry in ledger.values()
    )


def notify_state(ledger: dict, dispatch_entry: dict | None, terminal: bool) -> str:
    """Classify the child->parent hop finalization for one child.

    Notify entries carry no child id, so correlation goes through the
    dispatch ticket recorded in the same parent ledger.

    Args:
        ledger: Readable parent ledger ({} when it has no entries).
        dispatch_entry: The child's dispatch entry, or None when unmatched.
        terminal: Whether the child has reached a terminal state.

    Returns:
        "n/a" before terminality; otherwise "notified", "missing-notify",
        or "finalization-failed" when entries contradict.
    """
    if not terminal:
        return NOTIFY_NA
    if dispatch_entry is None or ledger_notify_conflict(ledger):
        return NOTIFY_FAILED
    ticket = str(dispatch_entry.get("ticket") or "")
    notified = any(
        isinstance(entry, dict)
        and entry.get("operation") == "notify"
        and str(entry.get("ticket") or "") == ticket
        for entry in ledger.values()
    )
    return NOTIFY_NOTIFIED if notified else NOTIFY_MISSING


def task_facts(
    row: dict[str, Any], ledger: dict | None, parent_known: bool
) -> dict[str, Any]:
    """Build one child's employee-task facts from the parent ledger.

    Args:
        row: Liveness row produced by classify().
        ledger: Readable parent ledger; None when unreadable.
        parent_known: Whether a parent ledger file was identified at all.

    Returns:
        Task object with dispatch facts plus the notify classification. Fact
        fields stay None when the ledger is unavailable, unreadable, or
        contradicts itself; ``notify`` and ``reason`` record which, and the
        liveness verdict is never affected.
    """
    terminal = row["verdict"] == "terminal"
    task: dict[str, Any] = {
        "ticket": None,
        "department": None,
        "request_id": None,
        "dispatch_status": None,
        "recorded_at": None,
        "notify": NOTIFY_NA,
        "reason": "",
    }
    if not parent_known:
        task["reason"] = "parent-ledger-unavailable"
        task["notify"] = NOTIFY_UNKNOWN if terminal else NOTIFY_NA
        return task
    if ledger is None:
        task["notify"] = NOTIFY_FAILED
        task["reason"] = "ledger-unreadable"
        return task
    entry, conflict = find_dispatch_entry(ledger, str(row["id"]))
    if entry is not None:
        task.update(
            ticket=str(entry.get("ticket") or "") or None,
            department=str(entry.get("department") or "") or None,
            request_id=str(entry.get("request_id") or "") or None,
            dispatch_status=str(entry.get("status") or "") or None,
            recorded_at=str(entry.get("recorded_at") or "") or None,
        )
    task["notify"] = notify_state(ledger, entry, terminal)
    task["reason"] = conflict or ""
    return task


def common_parent(rows: list[dict[str, Any]]) -> str:
    """Return the rows' single shared parent conversation id, else "".

    Args:
        rows: Liveness rows.

    Returns:
        The one distinct non-empty parent_conversation_id across rows, or ""
        when the rows have no parent or disagree on it.
    """
    parents = {str(row.get("parent_conversation_id") or "") for row in rows}
    parents.discard("")
    if len(parents) != 1:
        return ""
    return parents.pop()


def attach_task_facts(
    rows: list[dict[str, Any]], parent_id: str = ""
) -> list[dict[str, Any]]:
    """Attach per-child employee-task facts to liveness rows, read-only.

    Args:
        rows: Liveness rows from classify().
        parent_id: Explicit ledger parent; falls back to the rows' single
            common parent_conversation_id.

    Returns:
        The same rows, each with an additive ``task`` object. When no parent
        ledger can be identified, facts are marked unavailable while the
        liveness verdict stays untouched.
    """
    parent = parent_id.strip() or common_parent(rows)
    known = bool(parent)
    ledger = load_parent_ledger(parent) if known else None
    for row in rows:
        row["task"] = task_facts(row, ledger, known)
    return rows


def snapshot(
    ids: list[str],
    stall_sec: int,
    now: datetime | None = None,
    parent_id: str = "",
) -> list[dict[str, Any]]:
    clock = now or datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for cid in ids:
        conv = get_conversation(cid)
        event_at = last_event_at(cid) if conv is not None else None
        row = classify(conv, event_at, clock, stall_sec, cid)
        if row["verdict"] == "terminal":
            text = final_response(cid)
            if text:
                row["final_response"] = text
        rows.append(row)
    return attach_task_facts(rows, parent_id)


def report(
    children: list[dict[str, Any]], extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload = {
        "verdict": rollup(children),
        "children": children,
    }
    if extra:
        payload.update(extra)
    return payload


def ids_from_parent(parent_id: str) -> list[str]:
    conv = get_conversation(parent_id)
    if conv is None:
        raise SystemExit(f"parent not found: {parent_id}")
    raw = conv.get("sub_conversation_ids") or []
    ids = [str(x) for x in raw if x]
    if not ids:
        raise SystemExit(f"parent {parent_id} has no sub_conversation_ids")
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ids",
        action="append",
        default=[],
        help="Child ids, comma-separated. Repeatable.",
    )
    parser.add_argument(
        "--parent-id",
        default="",
        help="Use this conversation's sub_conversation_ids",
    )
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--poll-sec", type=int, default=30)
    parser.add_argument("--stall-sec", type=int, default=600)
    parser.add_argument("--timeout-sec", type=int, default=5400)
    args = parser.parse_args()

    ids = parse_ids(list(args.ids))
    if args.parent_id:
        for cid in ids_from_parent(args.parent_id.strip()):
            if cid not in ids:
                ids.append(cid)
    if not ids:
        raise SystemExit("need --ids or --parent-id")
    if len(ids) > 3:
        raise SystemExit("at most 3 child ids")
    if args.stall_sec <= 0 or args.timeout_sec <= 0:
        raise SystemExit("stall-sec and timeout-sec must be > 0")
    if args.loop and args.poll_sec <= 0:
        raise SystemExit("poll-sec must be > 0 with --loop")

    parent_id = args.parent_id.strip()

    if not args.loop:
        children = snapshot(ids, args.stall_sec, parent_id=parent_id)
        payload = report(children)
        print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
        sys.exit(exit_code(payload["verdict"], children))

    deadline = time.time() + args.timeout_sec
    last: dict[str, Any] | None = None
    while time.time() < deadline:
        children = snapshot(ids, args.stall_sec, parent_id=parent_id)
        last = report(children)
        line = " ".join(
            f"{row['id']}={row['verdict']}:{row['reason']}:{row['status']}"
            for row in children
        )
        print(line, file=sys.stderr, flush=True)
        if last["verdict"] != "alive":
            print(json.dumps(last, ensure_ascii=False, indent=2), flush=True)
            sys.exit(exit_code(last["verdict"], children))
        time.sleep(args.poll_sec)

    children = (
        last["children"]
        if last
        else snapshot(ids, args.stall_sec, parent_id=parent_id)
    )
    for row in children:
        if row["verdict"] == "alive":
            row["verdict"] = "hung"
            row["reason"] = "poll-timeout"
    payload = report(children)
    payload["verdict"] = "hung"
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
