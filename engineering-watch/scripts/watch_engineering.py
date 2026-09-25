#!/usr/bin/env python3
"""Engineering-layer watch over dispatched department child conversations.

Read-only. Classifies each child into the five-state taxonomy:
alive / hung / terminal + notified / terminal + missing-notify /
terminal + finalization-failed. Report arrival is proven only by a
correlated ``engineering:report`` in the parent conversation's events,
never by terminal state alone. Never mutates child state or the
dispatch ledger. Never prints the API key. Never POSTs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
_WATCH_SCRIPTS = str(REPO_ROOT / "openhands-watch" / "scripts")
if _WATCH_SCRIPTS not in sys.path:
    sys.path.insert(0, _WATCH_SCRIPTS)
_SESSIONS_SCRIPTS = str(REPO_ROOT / "openhands-sessions" / "scripts")
if _SESSIONS_SCRIPTS not in sys.path:
    sys.path.insert(0, _SESSIONS_SCRIPTS)

from watch import api, classify, final_response, get_conversation  # noqa: E402
from watch import ids_from_parent, parse_ids  # noqa: E402
from spawn import event_text_blob, request_identity  # noqa: E402,F401

REPORT_PREFIX = "engineering:report"
RESPONSE_ECHO_CAP = 160
FINALIZATION_MARKERS = (
    "notify fail",
    "notify failed",
    "finalization failed",
    "finalization-failed",
    "收尾失败",
)
REQUEST_LINE = re.compile(r"^\s*request:\s*(\S+)\s*$", re.M)
DEPARTMENT_LINE = re.compile(r"^\s*department:\s*(\S+)\s*$", re.M)
TICKET_LINE = re.compile(r"^\s*ticket:\s*(#\d+)\s*$", re.M)
EventReader = Callable[[str], list[str]]
ChildProber = Callable[[str, int, datetime], dict[str, Any]]


def report_fields(text: str) -> dict[str, str]:
    """Extract the correlation lines from one report text.

    Args:
        text: Candidate report text found in the parent event stream.

    Returns:
        Dict with ``first``, ``request``, ``department``, ``ticket`` keys;
        values are empty strings when absent.
    """
    stripped = text.lstrip()
    request = REQUEST_LINE.search(text)
    department = DEPARTMENT_LINE.search(text)
    ticket = TICKET_LINE.search(text)
    return {
        "first": stripped.splitlines()[0].strip() if stripped else "",
        "request": request.group(1) if request else "",
        "department": department.group(1) if department else "",
        "ticket": ticket.group(1) if ticket else "",
    }


def is_correlated_report(
    text: str,
    parent_id: str,
    department: str,
    ticket: str,
    request_id: str,
) -> bool:
    """Decide whether one parent event text is this request's report.

    The text must start with ``engineering:report`` and its ``request:`` /
    ``department:`` / ``ticket:`` lines must each match the expected dispatch
    identity parts; filters left empty only skip their own check. This mirrors
    the ``request_identity()`` form ``spawn.py`` dispatches under, so reports
    from unrelated requests or conversations never correlate.

    Args:
        text: One parent event text blob.
        parent_id: Expected parent conversation id.
        department: Expected department (empty = unchecked).
        ticket: Expected ticket ``#<n>`` (empty = unchecked).
        request_id: Expected logical request id (empty = unchecked).

    Returns:
        True when the blob is a correlated report for this dispatch.
    """
    if not text.lstrip().startswith(REPORT_PREFIX):
        return False
    fields = report_fields(text)
    if request_id and fields["request"] != request_id.strip():
        return False
    if department and fields["department"] != department.strip():
        return False
    if ticket and fields["ticket"] != ticket.strip():
        return False
    return True


def correlated_report(
    texts: list[str],
    parent_id: str,
    department: str,
    ticket: str,
    request_id: str,
) -> str | None:
    """Find the first correlated report among parent event texts.

    Args:
        texts: Text blobs from the parent conversation's event stream.
        parent_id: Expected parent conversation id.
        department: Expected department (empty = unchecked).
        ticket: Expected ticket ``#<n>`` (empty = unchecked).
        request_id: Expected logical request id (empty = unchecked).

    Returns:
        The first correlated report text, or None when absent.
    """
    for text in texts:
        if is_correlated_report(text, parent_id, department, ticket, request_id):
            return text
    return None


def finalization_failed(final_text: str | None) -> bool:
    """Decide whether a child's final response marks failed finalization.

    Args:
        final_text: Child ``final_response`` text (None when unavailable).

    Returns:
        True when the text carries a push / notify / finalization failure marker.
    """
    if not final_text:
        return False
    lowered = final_text.lower()
    return any(marker in lowered for marker in FINALIZATION_MARKERS)


def engineering_classify(
    row: dict[str, Any],
    parent_texts: list[str],
    parent_id: str,
    department: str = "",
    ticket: str = "",
    request_id: str = "",
) -> dict[str, Any]:
    """Classify one probe row into the five-state engineering taxonomy.

    Pure: copies the row, never mutates it, never touches any conversation.
    Non-terminal rows keep the probe's stall semantics (alive / hung).
    Terminal rows count as ``terminal + notified`` only with a correlated
    report; without it they surface as ``terminal + missing-notify``, or as
    ``terminal + finalization-failed`` when the final response marks failed
    finalization.

    Args:
        row: One row from the openhands-watch classifier.
        parent_texts: Parent event text blobs to search for the report.
        parent_id: Parent conversation id for the dispatch identity.
        department: Expected department (empty = unchecked).
        ticket: Expected ticket ``#<n>`` (empty = unchecked).
        request_id: Expected logical request id (empty = unchecked).

    Returns:
        A new row dict extended with ``engineering_status`` and ``report``
        evidence fields; terminal rows also carry a truncated
        ``final_response`` echo.
    """
    out = dict(row)
    final_text = row.get("final_response")
    if isinstance(final_text, str) and final_text:
        out["final_response"] = final_text[:RESPONSE_ECHO_CAP] + (
            "…" if len(final_text) > RESPONSE_ECHO_CAP else ""
        )
    verdict = row.get("verdict")
    if verdict != "terminal":
        out["engineering_status"] = verdict
        out["report"] = None
        return out
    found = correlated_report(parent_texts, parent_id, department, ticket, request_id)
    if found is not None:
        out["engineering_status"] = "terminal + notified"
        out["report"] = report_fields(found)
        return out
    out["report"] = None
    if finalization_failed(final_text if isinstance(final_text, str) else None):
        out["engineering_status"] = "terminal + finalization-failed"
    else:
        out["engineering_status"] = "terminal + missing-notify"
    return out


def rollup(children: list[dict[str, Any]]) -> str:
    """Roll child engineering statuses up to one payload verdict.

    Args:
        children: Rows extended by ``engineering_classify()``.

    Returns:
        ``alive`` when any child is alive, ``hung`` when any is hung,
        ``gap`` when any terminal child missed its notify, else ``notified``.
    """
    statuses = [str(row.get("engineering_status")) for row in children]
    if any(s == "alive" for s in statuses):
        return "alive"
    if any(s == "hung" for s in statuses):
        return "hung"
    if any(
        s in ("terminal + missing-notify", "terminal + finalization-failed")
        for s in statuses
    ):
        return "gap"
    return "notified"


def engineering_exit_code(verdict: str) -> int:
    """Map the payload verdict to the documented process exit code.

    Args:
        verdict: Verdict from ``rollup()``.

    Returns:
        0 all notified, 2 alive/hung, 3 terminal-with-gap, 1 otherwise.
    """
    if verdict == "notified":
        return 0
    if verdict in ("alive", "hung"):
        return 2
    if verdict == "gap":
        return 3
    return 1


def event_texts(payload: object) -> list[str]:
    """Flatten an events payload into per-event text blobs.

    Args:
        payload: ``GET /api/conversations/{id}/events`` payload, either a
            bare event list or a dict with an ``items`` list.

    Returns:
        One text blob per event, best-effort; empty events are dropped.
    """
    items: list[object] = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    return [blob for blob in (event_text_blob(item) for item in items) if blob]


def parent_event_texts(parent_id: str) -> list[str]:
    """Read the parent conversation's events as text blobs, best-effort.

    Read-only GET through the openhands-watch primitives. An unreadable
    events endpoint yields an empty list so report delivery stays unproven.

    Args:
        parent_id: Parent (planning) conversation id.

    Returns:
        One text blob per event; empty list when nothing readable.
    """
    try:
        payload = api("GET", f"/api/conversations/{parent_id}/events")
    except (SystemExit, OSError, ValueError):
        return []
    return event_texts(payload)


def probe_row(cid: str, stall_sec: int, now: datetime) -> dict[str, Any]:
    """Probe one child via openhands-watch and finalize its raw verdict.

    Read-only GETs through the openhands-watch primitives.

    Args:
        cid: Child conversation id (never invented; caller-supplied).
        stall_sec: Stall seconds passed through to the probe classifier.
        now: Snapshot clock.

    Returns:
        The classifier row; terminal rows gain a ``final_response``.
    """
    from watch import last_event_at

    conv = get_conversation(cid)
    event_at = last_event_at(cid) if conv is not None else None
    row = classify(conv, event_at, now, stall_sec, cid)
    if row["verdict"] == "terminal":
        text = final_response(cid)
        if text:
            row["final_response"] = text
    return row


def build_snapshot(
    ids: list[str],
    parent_id: str,
    stall_sec: int,
    department: str = "",
    ticket: str = "",
    request_id: str = "",
    now: datetime | None = None,
    event_reader: EventReader | None = None,
    prober: ChildProber | None = None,
) -> dict[str, Any]:
    """Build the engineering payload for these children of this parent.

    Read-only: probe GETs plus the parent events search. Never mutates
    child state or the dispatch ledger. Without ``parent_id`` no correlated
    report can be proven, so terminal children surface as gaps.

    Args:
        ids: Child ids from spawn JSON or ``--parent-id`` discovery.
        parent_id: Parent conversation id (report search scope; may be empty).
        stall_sec: Stall seconds for the probe's hung semantics.
        department: Expected department (empty = unchecked).
        ticket: Expected ticket ``#<n>`` (empty = unchecked).
        request_id: Expected logical request id (empty = unchecked).
        now: Snapshot clock (defaults to UTC now).
        event_reader: Parent events reader override for tests.
        prober: Per-child probe override for tests.

    Returns:
        Verdict JSON: ``verdict`` rollup plus per-child rows extended with
        ``engineering_status`` and ``report`` evidence fields.
    """
    clock = now or datetime.now(timezone.utc)
    read_events = event_reader or parent_event_texts
    probe_one = prober or probe_row
    texts = read_events(parent_id) if parent_id else []
    children = [
        engineering_classify(
            probe_one(cid, stall_sec, clock),
            texts,
            parent_id,
            department,
            ticket,
            request_id,
        )
        for cid in ids
    ]
    return {"verdict": rollup(children), "parent_id": parent_id, "children": children}


def main() -> None:
    """Run one read-only engineering snapshot from CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Read-only engineering watch over dispatched children."
    )
    parser.add_argument(
        "--ids",
        action="append",
        default=[],
        help="Child ids, comma-separated. Repeatable.",
    )
    parser.add_argument(
        "--parent-id",
        default="",
        help=(
            "Parent conversation id; discovers children"
            " and scopes the report search"
        ),
    )
    parser.add_argument(
        "--department",
        default="",
        help="Expected department of the dispatch",
    )
    parser.add_argument(
        "--ticket",
        default="",
        help="Expected ticket #<n> of the dispatch",
    )
    parser.add_argument(
        "--request-id",
        default="",
        help="Expected logical request id",
    )
    parser.add_argument("--stall-sec", type=int, default=600)
    args = parser.parse_args()

    parent_id = args.parent_id.strip()
    ids = parse_ids(list(args.ids))
    if not parent_id and not ids:
        raise SystemExit("need --ids or --parent-id")
    if args.stall_sec <= 0:
        raise SystemExit("stall-sec must be > 0")
    if parent_id and not ids:
        ids = ids_from_parent(parent_id)
    payload = build_snapshot(
        ids,
        parent_id,
        args.stall_sec,
        department=args.department.strip(),
        ticket=args.ticket.strip(),
        request_id=args.request_id.strip(),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    sys.exit(engineering_exit_code(payload["verdict"]))


if __name__ == "__main__":
    main()
