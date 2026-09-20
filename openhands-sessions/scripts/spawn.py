#!/usr/bin/env python3
"""Create an Agent Canvas conversation in this imported workspace. Never print the API key."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.environ.get("OPENHANDS_URL", "http://localhost:8000").rstrip("/")
KEY_PATH = Path.home() / ".openhands" / "agent-canvas" / "api-key.txt"
UI = os.environ.get("OPENHANDS_UI", "http://localhost:3001").rstrip("/")
WT_SEGMENT = re.compile(r"(?:^|[\\/])worktree(?:[\\/]|$)", re.I)
SIBLING_TREE = re.compile(r"-wt(?:-pr)?-\d+|[-_/]iso-\d+", re.I)


def api(method: str, path: str, body: dict | None = None, timeout: int = 60) -> object:
    key = KEY_PATH.read_text(encoding="utf-8").strip()
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "X-Session-API-Key": key,
        "X-Expose-Secrets": "encrypted",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(f"{BASE}{path}", data=data, headers=headers, method=method)
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
    try:
        payload = api("GET", f"/api/conversations/{cid}")
    except SystemExit as exc:
        if "HTTP 404" in str(exc):
            return None
        raise
    return payload if isinstance(payload, dict) else None


def working_dir_of(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    ws = payload.get("workspace") or {}
    if isinstance(ws, dict):
        wd = ws.get("working_dir")
        if isinstance(wd, str) and wd.strip():
            return wd
    return None


def norm_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(path.replace("/", os.sep)))


def refuse_path(path: str) -> str | None:
    p = path.replace("/", "\\")
    name = Path(path).name
    git = Path(path) / ".git"
    if WT_SEGMENT.search(path.replace("\\", "/")) or WT_SEGMENT.search(p):
        return "path has a worktree/ segment"
    if SIBLING_TREE.search(path):
        return "path looks like a ticket tree (*-wt-* / *-iso-*)"
    if git.is_file():
        return ".git is a file (linked worktree)"
    if name in {"master", "root"} and (Path(path).parent / "worktree").is_dir():
        return "imported the checkout; import the parent container"
    return None


def canvas_tags(parent: dict) -> dict[str, str]:
    tags = parent.get("tags") if isinstance(parent.get("tags"), dict) else {}
    out = {str(k): str(v) for k, v in tags.items() if k and v is not None}
    out["clientsource"] = "agentcanvas"
    return out


def status_of(payload: object) -> str:
    if not isinstance(payload, dict):
        return "unknown"
    for key in ("execution_status", "status", "conversation_status"):
        val = payload.get(key)
        if isinstance(val, str) and val:
            return val
    return "unknown"


def search_items(status: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, str] = {"limit": "100"}
    if status:
        params["status"] = status
    payload = api("GET", f"/api/conversations/search?{urlencode(params)}")
    if not isinstance(payload, dict):
        return []
    items = payload.get("items") or []
    return [x for x in items if isinstance(x, dict)]


def search_running() -> list[dict[str, Any]]:
    return search_items("running")


def imported_from_cwd(cwd: Path) -> Path | None:
    name = cwd.name
    parent = cwd.parent
    git = cwd / ".git"
    if name in {"master", "root"} and git.is_dir() and (parent / "worktree").is_dir():
        return parent
    if parent.name.lower() == "worktree":
        container = parent.parent
        if (container / "master").is_dir() or (container / "root").is_dir():
            return container
    if name.lower() == "worktree" and ((parent / "master").is_dir() or (parent / "root").is_dir()):
        return parent
    return None


def cwd_match_paths() -> list[str]:
    cwd = Path(os.path.abspath(str(Path.cwd())))
    out = [norm_path(str(cwd))]
    imported = imported_from_cwd(cwd)
    if imported is not None:
        n = norm_path(str(imported))
        if n not in out:
            out.append(n)
    return out


def is_workspace_hit(item: dict[str, Any], want: str) -> bool:
    wd = working_dir_of(item)
    if not wd or norm_path(wd) != want:
        return False
    tags = item.get("tags") if isinstance(item.get("tags"), dict) else {}
    if tags.get("clientsource") != "agentcanvas":
        return False
    return bool(item.get("id"))


def updated_key(item: dict[str, Any]) -> str:
    for key in ("updated_at", "created_at"):
        val = item.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


REPORT_PREFIX = "engineering:report"
DEPARTMENTS = {"delivery", "acceptance", "arbitration", "human", "planning"}
TERMINAL_STATES = {"finished", "stopped", "error"}
RESUMABLE_STATES = TERMINAL_STATES | {"paused", "idle", "awaiting_user"}


def report_fields(text: str) -> dict[str, str]:
    """Parse the report envelope without interpreting receipt details.

    Args:
        text: Report body beginning with ``engineering:report``.

    Returns:
        Lowercase envelope keys and stripped values.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        key, separator, value = line.partition(":")
        if separator:
            normalized = key.strip().lower()
            if normalized in fields:
                raise SystemExit(f"notify report duplicate field: {normalized}")
            fields[normalized] = value.strip()
    return fields


def validate_report(text: str, child: dict, allow_legacy: bool = False) -> str:
    """Validate report identity against its child conversation.

    Args:
        text: Complete engineering report.
        child: Current child conversation payload.
        allow_legacy: Permit an older report with no correlation envelope.

    Returns:
        ``exact`` or ``legacy-unverified`` correlation status.
    """
    fields = report_fields(text)
    required = {"dispatch-id", "child-conversation-id", "department", "ticket"}
    present = required.intersection(fields)
    if present != required:
        if not present and allow_legacy:
            return "legacy-unverified"
        missing = ", ".join(sorted(required - present))
        raise SystemExit(f"report identity missing: {missing}")
    tags = child.get("tags") if isinstance(child.get("tags"), dict) else {}
    expected = {
        "dispatch-id": tags.get("dispatch_id"),
        "child-conversation-id": str(child.get("id") or ""),
        "department": tags.get("department"),
        "ticket": tags.get("ticket"),
    }
    mismatches = [key for key in sorted(required) if str(fields[key]) != str(expected[key])]
    if mismatches:
        raise SystemExit(f"report identity mismatch: {', '.join(mismatches)}")
    return "exact"


def post_message(cid: str, text: str, run: bool) -> object:
    """Append a user message to an existing conversation.

    Args:
        cid: Existing Canvas conversation id.
        text: User message text.
        run: Whether the message API should request execution.

    Returns:
        API response payload.
    """
    payloads: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [{"type": "text", "text": text}],
            "run": run,
        },
        {
            "kind": "MessageEvent",
            "source": "user",
            "llm_message": {
                "role": "user",
                "content": [{"type": "text", "text": text}],
            },
            "run": run,
        },
    ]
    last: SystemExit | None = None
    for body in payloads:
        try:
            return api("POST", f"/api/conversations/{cid}/events", body)
        except SystemExit as exc:
            last = exc
            err = str(exc)
            if "HTTP 400" not in err and "HTTP 422" not in err:
                raise
    raise last or SystemExit("POST existing-conversation message failed")


def validate_resume(parent: dict, child: dict, parent_id: str, child_id: str) -> str:
    """Validate that planning may safely resume this department child.

    Args:
        parent: Current planning conversation payload.
        child: Requested child conversation payload.
        parent_id: Current planning conversation id.
        child_id: Requested child conversation id.

    Returns:
        Child status when the relationship is safe.
    """
    if child_id == parent_id:
        raise SystemExit("resume invalid direction: target is current conversation")
    if str(parent.get("id") or "") != parent_id:
        raise SystemExit("resume current conversation identity mismatch")
    if str(child.get("id") or "") != child_id:
        raise SystemExit("resume target identity mismatch")
    if parent.get("parent_conversation_id"):
        raise SystemExit("resume invalid direction: current conversation is not planning")
    if str(child.get("parent_conversation_id") or "") != parent_id:
        raise SystemExit("resume target is not a direct child of current planning conversation")
    if working_dir_of(child) != working_dir_of(parent):
        raise SystemExit("resume workspace mismatch")
    tags = child.get("tags") if isinstance(child.get("tags"), dict) else {}
    if tags.get("clientsource") != "agentcanvas":
        raise SystemExit("resume target missing clientsource=agentcanvas")
    if tags.get("layer") != "department" or tags.get("department") not in DEPARTMENTS - {"planning"}:
        raise SystemExit("resume target is not a dispatched department child")
    if not tags.get("dispatch_id") or not tags.get("ticket"):
        raise SystemExit("resume target missing dispatch identity")
    state = status_of(child)
    if state == "running":
        raise SystemExit("resume unsafe state: running")
    if state not in RESUMABLE_STATES:
        raise SystemExit(f"resume unsafe state: {state}")
    return state


def maybe_run(cid: str) -> None:
    try:
        api("POST", f"/api/conversations/{cid}/run", {})
    except SystemExit:
        return


def pick_workspace_id(items: list[dict[str, Any]], want: str) -> str | None:
    hits = [x for x in items if is_workspace_hit(x, want)]
    if not hits:
        return None
    hits.sort(key=updated_key, reverse=True)
    return str(hits[0]["id"])


def resolve_this(explicit: str | None) -> str:
    if explicit:
        conv = get_conversation(explicit)
        if conv and conv.get("id"):
            return str(conv["id"])
    for key in ("OPENHANDS_CONVERSATION_ID", "CONVERSATION_ID"):
        val = os.environ.get(key, "").strip()
        if not val:
            continue
        conv = get_conversation(val)
        if conv and conv.get("id"):
            return str(conv["id"])
    wants = cwd_match_paths()
    running = search_running()
    for want in wants:
        picked = pick_workspace_id(running, want)
        if picked:
            return picked
    items = search_items()
    for want in wants:
        picked = pick_workspace_id(items, want)
        if picked:
            return picked
    raise SystemExit(
        "cannot resolve this Canvas conversation id. "
        "Do not pass CURSOR_CONVERSATION_ID. Do not grep disk. Do not python -c GET."
    )


def ensure_child(cid: str, want_tags: dict[str, str]) -> dict:
    checked = get_conversation(cid)
    if checked is None:
        raise SystemExit("GET child failed")
    tags = checked.get("tags") if isinstance(checked.get("tags"), dict) else {}
    stored = checked.get("conversation_id")
    if tags.get("clientsource") != "agentcanvas":
        merged = {str(k): str(v) for k, v in tags.items() if k and v is not None}
        merged.update(want_tags)
        merged["clientsource"] = "agentcanvas"
        api("PATCH", f"/api/conversations/{cid}", {"tags": merged})
        checked = get_conversation(cid) or checked
    if stored in (None, ""):
        try:
            api("PATCH", f"/api/conversations/{cid}", {"conversation_id": cid})
            checked = get_conversation(cid) or checked
        except SystemExit:
            pass
    tags = checked.get("tags") if isinstance(checked.get("tags"), dict) else {}
    if tags.get("clientsource") != "agentcanvas":
        raise SystemExit(f"child tags missing clientsource=agentcanvas: {tags!r}")
    if not checked.get("id"):
        raise SystemExit("child id missing")
    return checked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("open", "dispatch", "this", "notify", "resume"), required=True
    )
    parser.add_argument("--this-id", default="", help="Canvas GET id. Not CURSOR_CONVERSATION_ID. Omit to resolve.")
    parser.add_argument("--profile-id", default="")
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--target-id", default="")
    parser.add_argument("--department", choices=sorted(DEPARTMENTS - {"planning"}))
    parser.add_argument("--ticket", default="")
    parser.add_argument("--dispatch-id", default="")
    parser.add_argument("--allow-legacy-report", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=500)
    parser.add_argument("--poll-sec", type=int, default=0)
    parser.add_argument("--timeout-sec", type=int, default=5400)
    args = parser.parse_args()

    this_id = resolve_this(args.this_id.strip() or None)
    parent = get_conversation(this_id)
    if parent is None:
        raise SystemExit("GET this conversation failed")
    if args.mode == "this":
        print(
            json.dumps(
                {
                    "id": parent.get("id") or this_id,
                    "working_dir": working_dir_of(parent),
                    "tags": parent.get("tags") if isinstance(parent.get("tags"), dict) else {},
                    "parent_conversation_id": parent.get("parent_conversation_id"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        return

    if args.mode == "resume":
        if not args.target_id or not args.prompt_file:
            raise SystemExit("resume needs --target-id and --prompt-file")
        child = get_conversation(args.target_id)
        if child is None:
            raise SystemExit("resume target GET failed")
        prior_state = validate_resume(parent, child, this_id, args.target_id)
        text = Path(args.prompt_file).read_text(encoding="utf-8")
        posted = post_message(args.target_id, text, run=False)
        api("POST", f"/api/conversations/{args.target_id}/run", {})
        print(
            json.dumps(
                {
                    "mode": "resume",
                    "parent_id": this_id,
                    "id": args.target_id,
                    "dispatch_id": child["tags"]["dispatch_id"],
                    "department": child["tags"]["department"],
                    "ticket": child["tags"]["ticket"],
                    "prior_status": prior_state,
                    "url": f"{UI}/conversations/{args.target_id}",
                    "posted": posted if isinstance(posted, dict) else True,
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        return

    if args.mode == "notify":
        if not args.prompt_file:
            raise SystemExit("notify needs --prompt-file")
        parent_id = parent.get("parent_conversation_id")
        if not parent_id:
            raise SystemExit("notify needs parent_conversation_id. Planning must not notify.")
        text = Path(args.prompt_file).read_text(encoding="utf-8")
        if not text.lstrip().startswith(REPORT_PREFIX):
            raise SystemExit("notify prompt must start with engineering:report")
        correlation = validate_report(text, parent, args.allow_legacy_report)
        target_id = str(parent_id)
        target = get_conversation(target_id)
        if target is None:
            raise SystemExit("notify parent GET failed")
        posted = post_message(target_id, text, run=True)
        if status_of(target) in TERMINAL_STATES:
            maybe_run(target_id)
        checked = get_conversation(target_id) or target
        child_tags = parent.get("tags") if isinstance(parent.get("tags"), dict) else {}
        print(
            json.dumps(
                {
                    "mode": "notify",
                    "this_id": this_id,
                    "child_conversation_id": parent.get("id") or this_id,
                    "parent_id": checked.get("id") or target_id,
                    "dispatch_id": child_tags.get("dispatch_id"),
                    "department": child_tags.get("department"),
                    "ticket": child_tags.get("ticket"),
                    "url": f"{UI}/conversations/{target_id}",
                    "parent_status": status_of(checked),
                    "correlation": correlation,
                    "posted": posted if isinstance(posted, dict) else True,
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        return

    if not args.profile_id or not args.prompt_file:
        raise SystemExit("open/dispatch need --profile-id and --prompt-file")
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    wd = working_dir_of(parent)
    if not wd:
        raise SystemExit("this conversation has no workspace.working_dir")
    why = refuse_path(wd)
    if why:
        raise SystemExit(f"refuse this conversation working_dir {wd!r}: {why}")

    child_id = str(uuid.uuid4())
    tags = canvas_tags(parent)
    dispatch_id = ""
    if args.mode == "dispatch" and (args.department or args.ticket or args.dispatch_id):
        if not args.department or not args.ticket:
            raise SystemExit("department dispatch needs --department and --ticket")
        dispatch_id = args.dispatch_id or str(uuid.uuid4())
        tags.update(
            {
                "layer": "department",
                "department": args.department,
                "ticket": args.ticket,
                "dispatch_id": dispatch_id,
            }
        )
    body: dict = {
        "conversation_id": child_id,
        "agent_profile_id": args.profile_id,
        "workspace": {"kind": "LocalWorkspace", "working_dir": wd},
        "confirmation_policy": {"kind": "NeverConfirm"},
        "max_iterations": args.max_iterations,
        "autotitle": True,
        "worktree": False,
        "tags": tags,
        "initial_message": {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
            "run": True,
        },
    }
    if args.mode == "dispatch":
        body["parent_conversation_id"] = this_id

    created = api("POST", "/api/conversations", body, timeout=120)
    if not isinstance(created, dict):
        raise SystemExit(f"unexpected create payload: {created!r}")
    cid = str(created.get("id") or created.get("conversation_id") or child_id)
    checked = ensure_child(cid, tags)
    got = working_dir_of(checked)
    if got != wd:
        raise SystemExit(f"working_dir mismatch: got {got!r} want {wd!r}")

    report = {
        "id": checked.get("id") or cid,
        "conversation_id": checked.get("conversation_id") or checked.get("id") or cid,
        "url": f"{UI}/conversations/{cid}",
        "mode": args.mode,
        "dispatch_id": dispatch_id or None,
        "child_conversation_id": checked.get("id") or cid,
        "department": args.department,
        "ticket": args.ticket or None,
        "working_dir": got,
        "tags": checked.get("tags") if isinstance(checked.get("tags"), dict) else {},
        "parent_conversation_id": checked.get("parent_conversation_id"),
        "max_iterations": args.max_iterations,
        "launched_agent_profile": checked.get("launched_agent_profile"),
        "this_id": this_id,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)

    if args.poll_sec <= 0:
        return
    terminal = {"finished", "error", "stopped"}
    deadline = time.time() + args.timeout_sec
    last = None
    while time.time() < deadline:
        time.sleep(args.poll_sec)
        cur = get_conversation(cid) or {}
        last = status_of(cur)
        if last in terminal:
            print(json.dumps({"id": cid, "status": last}, ensure_ascii=False), flush=True)
            if last != "finished":
                sys.exit(2)
            return
    raise SystemExit(f"poll timeout status={last!r}")


if __name__ == "__main__":
    main()
