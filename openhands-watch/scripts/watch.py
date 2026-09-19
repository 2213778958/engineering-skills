#!/usr/bin/env python3
"""Watch Agent Canvas child conversations. Never print the API key. Never POST."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.environ.get("OPENHANDS_URL", "http://localhost:8000").rstrip("/")
KEY_PATH = Path.home() / ".openhands" / "agent-canvas" / "api-key.txt"
UI = os.environ.get("OPENHANDS_UI", "http://localhost:3001").rstrip("/")

TERMINAL_OK = frozenset({"finished"})
TERMINAL_BAD = frozenset({"error", "stopped"})
HUNG_STATUS = frozenset(
    {"stuck", "waiting_for_confirmation", "paused", "deleting"}
)
RESPONSE_CAP = 2000


def api(method: str, path: str, timeout: int = 60) -> object:
    key = KEY_PATH.read_text(encoding="utf-8").strip()
    req = Request(
        f"{BASE}{path}",
        headers={
            "X-Session-API-Key": key,
            "X-Expose-Secrets": "encrypted",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {method} {path}: {err[:2000]}") from exc
    except URLError as exc:
        raise SystemExit(f"{method} {path} failed: {exc}") from exc


def get_conversation(cid: str) -> dict | None:
    key = KEY_PATH.read_text(encoding="utf-8").strip()
    req = Request(
        f"{BASE}/api/conversations/{cid}",
        headers={
            "X-Session-API-Key": key,
            "X-Expose-Secrets": "encrypted",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return payload if isinstance(payload, dict) else None
    except HTTPError as exc:
        if exc.code == 404:
            return None
        err = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} GET /api/conversations/{cid}: {err[:2000]}") from exc
    except URLError as exc:
        raise SystemExit(f"GET /api/conversations/{cid} failed: {exc}") from exc


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
    updated = conv.get("updated_at") if isinstance(conv.get("updated_at"), str) else None
    heartbeat = parse_ts(last_event) or parse_ts(updated) or parse_ts(conv.get("created_at"))
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
    if any(row.get("reason") not in {"finished"} and row["verdict"] == "terminal" for row in children):
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


def snapshot(ids: list[str], stall_sec: int, now: datetime | None = None) -> list[dict[str, Any]]:
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
    return rows


def report(children: list[dict[str, Any]], extra: dict[str, Any] | None = None) -> dict[str, Any]:
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
    parser.add_argument("--ids", action="append", default=[], help="Child ids, comma-separated. Repeatable.")
    parser.add_argument("--parent-id", default="", help="Use this conversation's sub_conversation_ids")
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

    if not args.loop:
        children = snapshot(ids, args.stall_sec)
        payload = report(children)
        print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
        sys.exit(exit_code(payload["verdict"], children))

    deadline = time.time() + args.timeout_sec
    last: dict[str, Any] | None = None
    while time.time() < deadline:
        children = snapshot(ids, args.stall_sec)
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

    children = last["children"] if last else snapshot(ids, args.stall_sec)
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
