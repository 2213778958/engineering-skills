#!/usr/bin/env python3
"""Create an Agent Canvas conversation in this imported workspace. Never print the API key."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE = os.environ.get("OPENHANDS_URL", "http://localhost:8000").rstrip("/")
KEY_PATH = Path.home() / ".openhands" / "agent-canvas" / "api-key.txt"
UI = os.environ.get("OPENHANDS_UI", "http://localhost:3001").rstrip("/")
WT_SEGMENT = re.compile(r"(?:^|[\\/])worktree(?:[\\/]|$)", re.I)
SIBLING_TREE = re.compile(r"-wt(?:-pr)?-\d+|[-_/]iso-\d+", re.I)
SECRET_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
AUTHORIZED_DEPARTMENTS = ("delivery", "acceptance", "arbitration", "human")
GITHUB_CONSUMER = "GH_TOKEN"
UUID_FORM = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
TICKET_FORM = re.compile(r"^#\d+$")
REQUEST_FORM = re.compile(r"^[0-9a-zA-Z][0-9a-zA-Z-]{7,63}$")
TERMINAL_STATES = {"finished", "error", "stopped"}
PROFILE_HINT = (
    "--profile-id takes the Agent Canvas profile UUID, not the human-readable "
    "profile name. Discover it from the agent-profile catalog "
    "(GET /api/agent-profiles, response key 'profiles', field 'id'), "
    "e.g. 123e4567-e89b-12d3-a456-426614174000."
)
PROFILE_ID_HELP = (
    "Agent Canvas profile UUID (GET /api/agent-profiles, key 'profiles'), "
    "not the profile name"
)
# Read window for event POSTs (notify/resume). A short window can let the
# backend persist the event but lose the HTTP response, which forces an
# unknown receipt and a duplicate-prone re-send; 180s matches the other
# long-timeout calls (dispatch create, child GET).
EVENT_POST_TIMEOUT = 180


def session_key() -> str:
    """Read the Canvas session API key.

    Returns:
        The key used only for authenticated local API requests.
    """
    try:
        key = KEY_PATH.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SystemExit("cannot read Canvas session authentication") from exc
    if not key:
        raise SystemExit("Canvas session authentication is empty")
    return key


def api(
    method: str,
    path: str,
    body: dict | None = None,
    timeout: int = 60,
    redact_error: bool = False,
) -> object:
    key = session_key()
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
        if redact_error:
            raise SystemExit(
                f"HTTP {exc.code} {method} request rejected (details redacted)"
            ) from exc
        err = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {method} {path}: {err[:2000]}") from exc
    except URLError as exc:
        if redact_error:
            raise SystemExit(f"{method} request failed (details redacted)") from exc
        raise SystemExit(f"{method} {path} failed: {exc}") from exc
    except TimeoutError as exc:
        raise SystemExit(f"{method} {path} timed out after {timeout}s") from exc


def github_binding(source: str, key: str) -> dict[str, dict[str, object]]:
    """Map a registered source secret to the child GitHub consumer.

    Args:
        source: Registered settings secret name declared by the process.
        key: Canvas session API key used by the authenticated lookup.

    Returns:
        A StartConversationRequest secrets mapping.
    """
    source = source.strip()
    if source.lower() == "none":
        raise SystemExit("GitHub credential binding is disabled (source is none)")
    if not source or not SECRET_NAME.fullmatch(source):
        raise SystemExit("GitHub credential source name is invalid")
    return {
        GITHUB_CONSUMER: {
            "kind": "LookupSecret",
            "url": f"{BASE}/api/settings/secrets/{quote(source, safe='')}",
            "headers": {"X-Session-API-Key": key},
            "description": "GitHub token for an authorized department",
        }
    }


def probe_secret_source(source: str, key: str) -> None:
    """Verify that the configured source exists and accepts authentication.

    Args:
        source: Registered settings secret name.
        key: Canvas session API key.
    """
    binding = github_binding(source, key)[GITHUB_CONSUMER]
    request = Request(
        str(binding["url"]),
        headers={"X-Session-API-Key": key, "Accept": "text/plain"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=30):
            return
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise SystemExit("GitHub credential source authentication failed") from exc
        if exc.code == 404:
            raise SystemExit("GitHub credential source is unavailable") from exc
        raise SystemExit("GitHub credential source lookup was rejected") from exc
    except URLError as exc:
        raise SystemExit("GitHub credential source is unavailable") from exc


def binding_status(bound: bool) -> dict[str, str]:
    """Return a non-secret diagnostic status for a conversation binding.

    Args:
        bound: Whether the secure lookup binding was attached.

    Returns:
        Sanitized consumer identity and state, or an empty mapping.
    """
    if not bound:
        return {}
    return {"consumer": GITHUB_CONSUMER, "status": "bound"}


def bound_department_prompt(prompt: str) -> str:
    """Add safe runtime preflight and finalization requirements.

    Args:
        prompt: Department task prompt.

    Returns:
        Prompt with no source name or credential value.
    """
    guidance = """GitHub credential binding: GH_TOKEN is securely bound for this department.
Before GitHub-dependent work, run this redacted PowerShell preflight exactly so regular
OpenHands sees the consumer name (ACP receives the subprocess environment):
`if (-not $env:GH_TOKEN) { throw 'GH_TOKEN unavailable' }; gh auth status`
Never print, log, persist, or pass the GH_TOKEN value as a command argument. Fail closed
if the variable or authentication is unavailable. If GitHub finalization fails, still
notify planning with the structured report and preserve completed receipts; report only
sanitized binding status.
"""
    return guidance + prompt


def conversation_body(
    child_id: str,
    profile_id: str,
    working_dir: str,
    prompt: str,
    tags: dict[str, str],
    max_iterations: int,
    parent_id: str | None = None,
    secrets: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build a child creation request without implicit credential inheritance.

    Args:
        child_id: Requested conversation UUID.
        profile_id: Agent profile UUID.
        working_dir: Imported workspace path.
        prompt: Initial task text.
        tags: Sanitized conversation tags.
        max_iterations: Agent iteration limit.
        parent_id: Optional department parent conversation.
        secrets: Explicit authorized-department secret mapping.

    Returns:
        StartConversationRequest-compatible payload.
    """
    body: dict[str, object] = {
        "conversation_id": child_id,
        "agent_profile_id": profile_id,
        "workspace": {"kind": "LocalWorkspace", "working_dir": working_dir},
        "confirmation_policy": {"kind": "NeverConfirm"},
        "max_iterations": max_iterations,
        "autotitle": True,
        "worktree": False,
        "tags": tags,
        "initial_message": {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
            "run": True,
        },
    }
    if parent_id:
        body["parent_conversation_id"] = parent_id
    if secrets:
        body["secrets"] = secrets
    return body


def get_conversation(cid: str, timeout: int = 60) -> dict | None:
    if not cid:
        return None
    try:
        payload = api("GET", f"/api/conversations/{cid}", timeout=timeout)
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
    """Read every page of conversations matching an optional status.

    Args:
        status: Optional server-side execution status filter.

    Returns:
        All conversation records returned by the paginated search.
    """
    limit = 100
    offset = 0
    cursor: str | None = None
    page_id: str | None = None
    seen_cursors: set[str] = set()
    seen_page_ids: set[str] = set()
    seen_pages: set[str] = set()
    items: list[dict[str, Any]] = []
    while True:
        params: dict[str, str] = {"limit": str(limit), "offset": str(offset)}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        if page_id:
            params["page_id"] = page_id
        payload = api("GET", f"/api/conversations/search?{urlencode(params)}")
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise SystemExit("conversation search returned an invalid payload")
        page = payload["items"]
        if any(not isinstance(item, dict) for item in page):
            raise SystemExit("conversation search returned an invalid item")

        next_page_id = payload.get("next_page_id")
        if next_page_id is not None and (
            not isinstance(next_page_id, str)
            or not next_page_id
            or next_page_id in seen_page_ids
        ):
            raise SystemExit("conversation search returned an invalid next page id")
        next_cursor = payload.get("next_cursor")
        if next_page_id is None and next_cursor is not None and (
            not isinstance(next_cursor, str)
            or not next_cursor
            or next_cursor in seen_cursors
        ):
            raise SystemExit("conversation search returned an invalid next cursor")

        page_fingerprint = json.dumps(page, sort_keys=True, separators=(",", ":"))
        if page and page_fingerprint in seen_pages:
            raise SystemExit("conversation search returned a repeated page")
        if page:
            seen_pages.add(page_fingerprint)
        items.extend(page)

        if next_page_id is not None:
            seen_page_ids.add(next_page_id)
            page_id = next_page_id
            cursor = None
            continue
        if next_cursor is not None:
            seen_cursors.add(next_cursor)
            cursor = next_cursor
            page_id = None
            continue
        has_more = payload.get("has_more") is True
        total = payload.get("total")
        if isinstance(total, int):
            has_more = has_more or len(items) < total
        if not has_more and len(page) < limit:
            return items
        if not page:
            raise SystemExit("conversation search pagination made no progress")
        offset += len(page)


def search_running() -> list[dict[str, Any]]:
    return search_items("running")


def validate_profile_id(profile_id: str) -> str:
    """Fail closed unless profile_id is the Agent Canvas profile UUID form.

    Args:
        profile_id: Value passed as --profile-id (may be empty).

    Returns:
        The stripped profile UUID.

    Raises:
        SystemExit: If the value is name-shaped instead of a UUID.
    """
    if not profile_id:
        return ""
    cleaned = profile_id.strip()
    if UUID_FORM.fullmatch(cleaned):
        return cleaned
    raise SystemExit(PROFILE_HINT)


def normalize_ticket(value: str) -> str:
    """Validate the ticket scope of a dispatch/resume identity.

    Args:
        value: Raw --ticket value.

    Returns:
        The ticket in ``#<n>`` form.

    Raises:
        SystemExit: If the value is not ``#<n>``.
    """
    cleaned = value.strip()
    if TICKET_FORM.fullmatch(cleaned):
        return cleaned
    raise SystemExit("--ticket must look like '#41' (a ticket number)")


def normalize_request_id(value: str) -> str:
    """Validate the logical request id of an operation identity.

    Args:
        value: Raw --request-id value.

    Returns:
        The stripped opaque request id.

    Raises:
        SystemExit: If the value is too short or not opaque id material.
    """
    cleaned = value.strip()
    if REQUEST_FORM.fullmatch(cleaned):
        return cleaned
    raise SystemExit(
        "--request-id must be an opaque logical request id "
        "(uuid or hex, 8-64 characters) scoping this one intentional request"
    )


def request_identity(
    parent_id: str, department: str, ticket: str, request_id: str
) -> str:
    """Build the request-scoped dispatch identity string.

    Args:
        parent_id: Parent conversation that owns the dispatch.
        department: Authorized destination department.
        ticket: Ticket scope (``#<n>``).
        request_id: Caller-supplied logical request id.

    Returns:
        Identity covering parent, department, ticket, and logical request.
    """
    return f"dispatch:{parent_id}:{department}:{ticket}:{request_id}"


def dispatch_request_child_id(
    parent_id: str, department: str, ticket: str, request_id: str
) -> str:
    """Return the server uniqueness key for a request-scoped dispatch.

    Args:
        parent_id: Planning conversation that owns the dispatch.
        department: Authorized destination department.
        ticket: Ticket scope (``#<n>``).
        request_id: Caller-supplied logical request id.

    Returns:
        Stable UUID shared only by retries of this exact logical request.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, request_identity(
        parent_id, department, ticket, request_id
    )))


def prompt_digest(text: str) -> str:
    """Hash prompt text for payload-collision detection.

    Args:
        text: Prompt or report text.

    Returns:
        Hex sha256 digest.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ledger_dir() -> Path:
    """Resolve the dispatch ledger directory.

    Returns:
        Directory holding per-parent ledger files. The env override exists
        for test isolation only.
    """
    override = os.environ.get("OPENHANDS_DISPATCH_LEDGER_DIR", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".openhands" / "agent-canvas" / "dispatch-ledger"


def ledger_path(parent_id: str) -> Path:
    """Resolve the ledger file for one parent conversation.

    Args:
        parent_id: Parent conversation UUID (ledger key).

    Returns:
        Path to the parent's JSON ledger file.

    Raises:
        SystemExit: If the parent id is not a UUID (traversal guard).
    """
    if not UUID_FORM.fullmatch(parent_id.strip()):
        raise SystemExit(
            "conversation id is not a UUID; refusing ledger access "
            f"for {parent_id!r}"
        )
    return ledger_dir() / f"{parent_id.strip()}.json"


def load_ledger(parent_id: str) -> dict[str, dict]:
    """Read the per-parent request ledger, failing closed when unreadable.

    Args:
        parent_id: Parent conversation UUID (ledger key).

    Returns:
        Mapping of request id to recorded request entry.

    Raises:
        SystemExit: If the ledger file exists but cannot be parsed.
    """
    path = ledger_path(parent_id)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(
            f"dispatch ledger {path} is unreadable; reconcile manually, "
            "fail-closed"
        ) from exc
    return payload if isinstance(payload, dict) else {}


def save_ledger(parent_id: str, ledger: dict[str, dict]) -> None:
    """Atomically persist the per-parent request ledger.

    Args:
        parent_id: Parent conversation UUID (ledger key).
        ledger: Full ledger mapping to write.
    """
    path = ledger_path(parent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(ledger, fh, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def record_ledger(parent_id: str, request_id: str, entry: dict) -> None:
    """Record one request entry in the parent's ledger.

    Args:
        parent_id: Parent conversation UUID (ledger key).
        request_id: Logical request id key.
        entry: Entry payload (ids, hashes, receipt status; never secrets).
    """
    ledger = load_ledger(parent_id)
    ledger[request_id] = entry
    save_ledger(parent_id, ledger)


def ledger_entry(
    *,
    operation: str,
    request_id: str,
    ticket: str,
    department: str,
    parent_id: str,
    status: str,
    evidence: str,
    target_id: str = "",
    child_id: str = "",
    prompt_sha256: str = "",
    profile_id: str = "",
    working_dir: str = "",
    identity: str = "",
    attempts: int = 1,
) -> dict:
    """Build a structured, secret-free ledger entry.

    Args:
        operation: dispatch / resume / notify.
        request_id: Logical request id.
        ticket: Ticket scope.
        department: Department scope (empty for notify).
        parent_id: Ledger-owning conversation.
        status: accepted / unknown / rejected.
        evidence: Short receipt evidence string.
        target_id: Resumed/posted target conversation.
        child_id: Created child conversation.
        prompt_sha256: Payload digest for collision detection.
        profile_id: Agent profile UUID used.
        working_dir: Workspace used.
        identity: Full request identity string.
        attempts: Number of mutating attempts recorded.

    Returns:
        Ledger entry dict (no credentials, no secrets).
    """
    return {
        "operation": operation,
        "request_id": request_id,
        "identity": identity or request_identity(parent_id, department, ticket, request_id),
        "ticket": ticket,
        "department": department,
        "parent_id": parent_id,
        "child_id": child_id,
        "target_id": target_id,
        "prompt_sha256": prompt_sha256,
        "profile_id": profile_id,
        "working_dir": working_dir,
        "status": status,
        "evidence": evidence,
        "attempts": attempts,
        "recorded_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(timespec="seconds"),
    }


def make_receipt(
    status: str,
    *,
    operation: str,
    request_id: str,
    ticket: str,
    department: str,
    parent_id: str,
    target_id: str = "",
    evidence: str = "",
    next_action: str = "",
    **extra: object,
) -> dict:
    """Build a structured accepted/unknown/rejected receipt.

    Args:
        status: accepted (API acceptance only), unknown (unproven), rejected.
        operation: dispatch / resume / notify.
        request_id: Logical request id.
        ticket: Ticket scope.
        department: Department scope.
        parent_id: Parent/source conversation.
        target_id: Child/target conversation.
        evidence: Short evidence string.
        next_action: Safe next action for the caller.
        **extra: Additional receipt fields.

    Returns:
        Receipt dict.
    """
    actions = {
        "accepted": (
            "accepted means API acceptance only, not work completion; "
            "when polling is disabled, return immediately"
        ),
        "unknown": (
            "GET the child status before retrying; never retry an active "
            "or unknown child; reconcile with the same --request-id"
        ),
        "rejected": (
            "fix the request and use a new --request-id; do not retry "
            "unchanged"
        ),
    }
    receipt = {
        "receipt": status,
        "operation": operation,
        "request_id": request_id,
        "ticket": ticket,
        "department": department,
        "parent_id": parent_id,
        "target_id": target_id,
        "evidence": evidence,
        "next_action": next_action or actions.get(status, ""),
    }
    receipt.update(extra)
    return receipt


def emit_receipt(receipt: dict) -> None:
    """Print a structured receipt as JSON on stdout.

    Args:
        receipt: Receipt from make_receipt.
    """
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)


def http_op(
    method: str,
    path: str,
    body: dict | None = None,
    timeout: int = 60,
    redact_error: bool = False,
    *,
    operation: str,
    request_id: str,
    ticket: str = "",
    department: str = "",
    parent_id: str = "",
    target_id: str = "",
    emit: bool = True,
) -> tuple[object, dict, BaseException | None]:
    """Perform one mutating API operation and classify its receipt.

    Args:
        method: HTTP method (POST expected for dispatch/resume/notify).
        path: API path.
        body: JSON body.
        timeout: Client timeout in seconds.
        redact_error: Redact rejection details (credential-bound flows).
        operation: dispatch / resume / notify.
        request_id: Logical request id.
        ticket: Ticket scope.
        department: Department scope.
        parent_id: Parent/source conversation.
        target_id: Child/target conversation.
        emit: Print the receipt (False for intermediate fallback attempts).

    Returns:
        (payload, receipt, error). error is None on accepted; otherwise the
        original SystemExit/TimeoutError for the caller to record and raise.
    """
    try:
        payload = api(method, path, body, timeout=timeout, redact_error=redact_error)
    except SystemExit as exc:
        message = str(exc)
        code = re.search(r"HTTP (\d{3})", message)
        if "timed out" in message or "failed" in message:
            status = "unknown"
            evidence = (
                f"{method} {path} timed out or response lost; "
                "acceptance unproven (never claim exactly-once)"
            )
            if redact_error:
                evidence = f"{method} request timed out or response lost (details redacted)"
        else:
            status = "rejected"
            evidence = message[:200] if not redact_error else (
                f"HTTP {code.group(1) if code else '?'} rejected (details redacted)"
            )
        receipt = make_receipt(
            status,
            operation=operation,
            request_id=request_id,
            ticket=ticket,
            department=department,
            parent_id=parent_id,
            target_id=target_id,
            evidence=evidence,
        )
        if emit:
            emit_receipt(receipt)
        return None, receipt, exc
    except TimeoutError as exc:
        receipt = make_receipt(
            "unknown",
            operation=operation,
            request_id=request_id,
            ticket=ticket,
            department=department,
            parent_id=parent_id,
            target_id=target_id,
            evidence=(
                f"{method} {path} timed out or response lost; "
                "acceptance unproven (never claim exactly-once)"
            ),
        )
        if emit:
            emit_receipt(receipt)
        return None, receipt, exc
    receipt = make_receipt(
        "accepted",
        operation=operation,
        request_id=request_id,
        ticket=ticket,
        department=department,
        parent_id=parent_id,
        target_id=target_id,
        evidence=f"{method} {path} accepted by API response",
    )
    if emit:
        emit_receipt(receipt)
    return payload, receipt, None


def refuse_duplicate_dispatch(
    parent_id: str, tags: dict[str, str], force: bool = False
) -> None:
    """Reject a duplicate active department child for the same parent.

    Args:
        parent_id: Planning conversation that owns the dispatch.
        tags: Child tags, including the department when available.
        force: Explicitly bypass the duplicate guard.
    """
    if force:
        return
    department = tags.get("department", "")
    if not department:
        return
    terminal = {"finished", "error", "stopped"}
    duplicates = []
    for item in search_items():
        if str(item.get("parent_conversation_id") or "") != parent_id:
            continue
        item_tags = item.get("tags") if isinstance(item.get("tags"), dict) else {}
        if str(item_tags.get("department") or "") != department:
            continue
        if status_of(item) not in terminal:
            duplicates.append(item)
    if duplicates:
        details = ", ".join(
            f"{item.get('id')} ({UI}/conversations/{item.get('id')})"
            for item in duplicates
        )
        raise SystemExit(
            f"active {department} dispatch already exists: {details}; use --force to bypass"
        )


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
REPORT_HOPS = {
    "done",
    "send-back",
    "need-arbitration",
    "need-human",
    "blocked",
    "wait-merge",
}
TERMINAL_STATES = {"finished", "stopped", "error"}
NON_TERMINAL_RESUMABLE_STATES = {"paused", "idle", "awaiting_user"}
RESUMABLE_STATES = TERMINAL_STATES | NON_TERMINAL_RESUMABLE_STATES


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
    """Validate a complete report envelope against its child conversation.

    Args:
        text: Complete engineering report.
        child: Current child conversation payload.
        allow_legacy: Permit a complete older report with no correlation identity.

    Returns:
        ``exact`` or ``legacy-unverified`` correlation status.
    """
    fields = report_fields(text)
    identity = {"dispatch-id", "child-conversation-id", "department", "ticket"}
    operational = {"hop", "receipts", "suggested next"}
    present_identity = identity.intersection(fields)
    missing_operational = sorted(
        key for key in operational if not fields.get(key, "").strip()
    )
    if missing_operational:
        raise SystemExit(
            f"report envelope missing: {', '.join(missing_operational)}"
        )
    if fields["hop"] not in REPORT_HOPS:
        raise SystemExit(f"report hop invalid: {fields['hop']}")
    if present_identity != identity:
        if not present_identity and allow_legacy:
            return "legacy-unverified"
        missing = ", ".join(sorted(identity - present_identity))
        raise SystemExit(f"report identity missing: {missing}")
    empty_identity = sorted(key for key in identity if not fields[key].strip())
    if empty_identity:
        raise SystemExit(f"report identity empty: {', '.join(empty_identity)}")
    tags = child.get("tags") if isinstance(child.get("tags"), dict) else {}
    expected = {
        "dispatch-id": tags.get("dispatch_id"),
        "child-conversation-id": str(child.get("id") or ""),
        "department": tags.get("department"),
        "ticket": tags.get("ticket"),
    }
    mismatches = [
        key for key in sorted(identity) if str(fields[key]) != str(expected[key])
    ]
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
    # F2 (issue #24): the resume direction must be planning-root ->
    # direct child. A caller with a parent, or a caller not marked as a
    # planning conversation, may not resume anything.
    if child.get("parent_conversation_id"):
        raise SystemExit(
            "resume rejected: caller must be a parentless planning root; "
            "planning must not resume as a child"
        )
    tags = child.get("tags") if isinstance(child.get("tags"), dict) else {}
    layer = str(tags.get("layer") or "")
    department = str(tags.get("department") or "")
    if layer and layer != "planning":
        raise SystemExit(
            "resume rejected: caller layer is not planning "
            f"(layer={layer!r}); resume is planning-root -> direct child"
        )
    if department and department != "planning":
        raise SystemExit(
            "resume rejected: caller has a non-planning department tag "
            f"(department={department!r}); resume is planning-root -> direct child"
        )
    return state


def event_payload(text: str) -> dict[str, Any]:
    """Build the user-message event payload that persists the full text.

    The kind-style ``MessageEvent`` form is also accepted by the API with a
    2xx response, but the backend persists it with an empty ``content`` list
    (#49), silently dropping the continuation. The role-style user message
    is the form the backend demonstrably persists; ``run`` stays ``True`` so
    the single event POST still triggers the run.

    Args:
        text: Report or continuation text.

    Returns:
        Payload dict for ``POST /api/conversations/{id}/events``.
    """
    return {
        "role": "user",
        "content": [{"type": "text", "text": text}],
        "run": True,
    }


def send_event(
    cid: str, text: str, poster, ctx: dict
) -> tuple[object, dict, BaseException | None]:
    """POST the continuation/report event to one conversation via the adapter.

    Args:
        cid: Target conversation (parent for notify, exact child for resume).
        text: Report or continuation text.
        poster: Callable (method, path, body, emit) -> (payload, receipt, err).
        ctx: Receipt context (operation/request_id/ticket/department/...).

    Returns:
        The result of the single event POST. Explicit backend rejection is
        terminal; ambiguous transport failure is reconciled by the ledger.
    """
    return poster(
        "POST",
        f"/api/conversations/{cid}/events",
        event_payload(text),
        True,
    )


def event_text_blob(event: object) -> str:
    """Flatten the persisted text fragments of one event into one string.

    Args:
        event: Persisted event payload (role-style or kind-style shape).

    Returns:
        Concatenated text content; empty when the event carries no text.
    """
    if not isinstance(event, dict):
        return ""
    parts: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, str):
            parts.append(node)
            return
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if isinstance(node, dict):
            text = node.get("text")
            if isinstance(text, str):
                parts.append(text)
                return
            for key in ("content", "message"):
                if key in node:
                    walk(node[key])

    walk(event)
    return "\n".join(part for part in parts if part)


def target_event_texts(cid: str) -> list[str]:
    """Read the target conversation's recent events as text blobs.

    Args:
        cid: Conversation whose persisted events are read.

    Returns:
        One text blob per event, best-effort. An unreadable events endpoint
        (missing, rejected, timed out) yields an empty list so callers treat
        delivery as unproven and keep the bounded re-send as the fallback.
    """
    try:
        payload = api("GET", f"/api/conversations/{cid}/events")
    except (SystemExit, TimeoutError):
        return []
    items: list[object] = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    blobs = [event_text_blob(event) for event in items]
    return [blob for blob in blobs if blob]


def event_marker(text: str) -> str:
    """Return the persisted-event marker that proves this request landed.

    The report/continuation text is persisted verbatim (role-style event
    payload), so the exact stripped text doubles as the delivery marker:
    matching it proves this very text landed, not just a sibling report
    carrying the same ``request:`` correlation line from the same hop.

    Args:
        text: Report or continuation text that was posted.

    Returns:
        The stripped text used as the events marker.
    """
    return text.strip()


def reconcile_event_marker(
    target_id: str, text: str, ctx: dict, entry: dict
) -> str:
    """Reconcile an unknown event receipt against the target's events.

    GETs the target conversation's recent events and searches for this
    request's marker (see event_marker). Marker found means the earlier
    POST persisted despite the lost response; a reconciled accepted receipt
    is recorded and no re-send fires. Marker absent keeps the single
    bounded re-send as the liveness fallback.

    Args:
        target_id: Conversation the event was posted to (and read back).
        text: Report or continuation text that was posted.
        ctx: Receipt context fields.
        entry: Prior ledger entry (status unknown) to preserve attempts on.

    Returns:
        "reconciled" when prior delivery is proven (receipt emitted, ledger
        updated), "resend" when delivery remains unproven.
    """
    marker = event_marker(text)
    found = bool(marker) and any(
        marker in blob for blob in target_event_texts(target_id)
    )
    if not found:
        return "resend"
    emit_receipt(
        reconciled_receipt(
            "unknown", "text marker found in target events", ctx
        )
    )
    updated = dict(entry)
    updated["status"] = "accepted"
    updated["evidence"] = "reconciled from unknown: marker in target events"
    record_ledger(ctx["parent_id"], ctx["request_id"], updated)
    return "reconciled"


def refuse_duplicate_from_ledger(
    parent_id: str,
    department: str,
    request_id: str,
    ledger: dict[str, dict],
    force: bool,
) -> None:
    """Refuse an active same-department dispatch recorded for this parent.

    Ledger-driven bounded guard: consults only recorded receipts and
    reconciles specific candidates with targeted GETs (never a full search).

    Args:
        parent_id: Parent conversation UUID.
        department: Requested department.
        request_id: Current logical request id (excluded from the guard).
        ledger: Loaded per-parent ledger.
        force: Explicit intentional bypass of this guard only.
    """
    if force:
        return
    for rid, entry in sorted(ledger.items()):
        if rid == request_id:
            continue
        if entry.get("operation") != "dispatch":
            continue
        if entry.get("department") != department:
            continue
        if entry.get("status") not in {"accepted", "unknown"}:
            continue
        child = get_conversation(str(entry.get("child_id") or ""))
        if child is not None and status_of(child) not in TERMINAL_STATES:
            raise SystemExit(
                f"active {department} dispatch already exists "
                f"(request {rid}, child {entry.get('child_id')}): "
                "use --force to bypass"
            )


def verify_request_payload(
    entry: dict,
    department: str,
    ticket: str,
    profile_id: str,
    wd: str,
    digest: str,
    request_id: str,
) -> None:
    """Fail closed when a known request id arrives with a changed payload.

    Args:
        entry: Prior ledger entry for this request id.
        department: Requested department.
        ticket: Requested ticket scope.
        profile_id: Requested profile UUID.
        wd: Requested workspace dir.
        digest: Prompt digest.
        request_id: Logical request id.

    Raises:
        SystemExit: On any identity/payload mismatch (before any POST).
    """
    mismatched = []
    if entry.get("department") != department:
        mismatched.append("department")
    if entry.get("ticket") != ticket:
        mismatched.append("ticket")
    if entry.get("profile_id") != profile_id:
        mismatched.append("profile")
    if norm_path(str(entry.get("working_dir") or "")) != norm_path(wd):
        mismatched.append("workspace")
    if entry.get("prompt_sha256") != digest:
        mismatched.append("prompt")
    if mismatched:
        raise SystemExit(
            f"request identity collision: --request-id {request_id} was "
            f"recorded with a different {', '.join(mismatched)}; fail-closed, "
            "use a new --request-id"
        )


def reconciled_receipt(
    prior: str, evidence: str, ctx: dict
) -> dict:
    """Build an accepted receipt reconciled from a prior ledger receipt.

    Args:
        prior: Prior receipt status from the ledger.
        evidence: Reconciliation evidence.
        ctx: Receipt context fields.

    Returns:
        Accepted receipt with reconciled evidence.
    """
    return make_receipt(
        "accepted",
        reconciled=True,
        evidence=f"reconciled: prior receipt {prior}; {evidence}",
        **ctx,
    )


def reconcile_dispatch_entry(
    parent_id: str, department: str, ticket: str, request_id: str, entry: dict
) -> str:
    """Reconcile a prior dispatch receipt with targeted GETs only.

    Args:
        parent_id: Parent conversation UUID.
        department: Department scope.
        ticket: Ticket scope.
        request_id: Logical request id.
        entry: Prior ledger entry.

    Returns:
        "reconciled" when no create is needed, "recreate" for the bounded
        same-identity re-create.

    Raises:
        SystemExit: On rejected priors, unsafe states, or exhausted bounds.
    """
    ctx = {
        "operation": "dispatch",
        "request_id": request_id,
        "ticket": ticket,
        "department": department,
        "parent_id": parent_id,
        "target_id": str(entry.get("child_id") or ""),
    }
    status = str(entry.get("status") or "unknown")
    attempts = int(entry.get("attempts", 0))
    if status == "rejected":
        raise SystemExit(
            f"request {request_id} was previously rejected; do not retry "
            f"unchanged (evidence: {str(entry.get('evidence', ''))[:200]})"
        )
    child_ref = str(entry.get("child_id") or "")
    child = get_conversation(child_ref)
    state = status_of(child)
    if child is not None and state == "running":
        emit_receipt(
            reconciled_receipt(status, f"child {child_ref} is running", ctx)
        )
        entry = dict(entry)
        entry["status"] = "accepted"
        entry["evidence"] = f"reconciled from {status}: child running"
        record_ledger(parent_id, request_id, entry)
        return "reconciled"
    if child is not None and state == "finished":
        if status in {"accepted", "unknown"}:
            if status == "accepted":
                emit_receipt(
                    reconciled_receipt(status, f"child {child_ref} finished", ctx)
                )
                return "reconciled"
            emit_receipt(
                make_receipt(
                    "unknown",
                    evidence=(
                        "target child finished but prior dispatch acceptance remains "
                        "unproven; no blind create retry"
                    ),
                    **ctx,
                )
            )
            raise SystemExit(1)
        emit_receipt(
            make_receipt(
                "unknown",
                evidence=(
                    "bounded same-request re-send exhausted; child finished; "
                    "delivery remains unproven"
                ),
                **ctx,
            )
        )
        raise SystemExit(1)
    if child is not None and state == "error":
        if attempts < 2:
            return "recreate"
        raise SystemExit(
            f"child {child_ref} is in error and the bounded same-identity "
            "re-create is exhausted; do not retry blindly"
        )
    if child is None:
        if attempts < 2:
            return "recreate"
        raise SystemExit(
            f"recorded child {child_ref} is absent and the bounded "
            "same-identity re-create is exhausted; do not retry blindly"
        )
    raise SystemExit(
        f"child {child_ref} state {state!r} is not safely resumable; "
        "do not retry"
    )


def run_dispatch(args: argparse.Namespace, parent: dict, this_id: str = "") -> None:
    """Dispatch a department child under a request-scoped identity.

    Args:
        args: Parsed CLI arguments.
        parent: This (planning) conversation payload.
        this_id: Canvas id of this conversation (defaults to parent id).
    """
    this_id = this_id or str(parent.get("id") or "")
    department = args.department or ""
    if not department:
        raise SystemExit("dispatch needs --department")
    profile_id = validate_profile_id(args.profile_id)
    if not profile_id:
        raise SystemExit("dispatch needs --profile-id")
    ticket = normalize_ticket(args.ticket)
    request_id = normalize_request_id(args.request_id)
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    wd = working_dir_of(parent)
    if not wd:
        raise SystemExit("this conversation has no workspace.working_dir")
    why = refuse_path(wd)
    if why:
        raise SystemExit(f"refuse this conversation working_dir {wd!r}: {why}")
    wants_binding = bool(args.github_token_secret)
    secrets = None
    if wants_binding:
        key = session_key()
        probe_secret_source(args.github_token_secret, key)
        secrets = github_binding(args.github_token_secret, key)
        prompt = bound_department_prompt(prompt)
    digest = prompt_digest(prompt)
    ledger = load_ledger(this_id)
    entry = ledger.get(request_id)
    if entry is not None:
        verify_request_payload(
            entry, department, ticket, profile_id, wd, digest, request_id
        )
        if reconcile_dispatch_entry(this_id, department, ticket, request_id, entry) == "reconciled":
            return
    else:
        refuse_duplicate_from_ledger(this_id, department, request_id, ledger, args.force)
        if args.force:
            refuse_duplicate_dispatch(this_id, {"department": department}, force=True)
    child_id = str((entry or {}).get("child_id") or "") or dispatch_request_child_id(
        this_id, department, ticket, request_id
    )
    tags = canvas_tags(parent)
    tags["department"] = department
    body = conversation_body(
        child_id=child_id,
        profile_id=profile_id,
        working_dir=wd,
        prompt=prompt,
        tags=tags,
        max_iterations=args.max_iterations,
        parent_id=this_id,
        secrets=secrets,
    )
    payload, receipt, err = http_op(
        "POST",
        "/api/conversations",
        body,
        timeout=180,
        redact_error=wants_binding,
        operation="dispatch",
        request_id=request_id,
        ticket=ticket,
        department=department,
        parent_id=this_id,
        target_id=child_id,
    )
    attempts = int((entry or {}).get("attempts", 0)) + 1
    if err is not None:
        record_ledger(
            this_id,
            request_id,
            ledger_entry(
                operation="dispatch",
                request_id=request_id,
                ticket=ticket,
                department=department,
                parent_id=this_id,
                status=receipt["receipt"],
                evidence=receipt["evidence"],
                child_id=child_id,
                prompt_sha256=digest,
                profile_id=profile_id,
                working_dir=wd,
                attempts=attempts,
            ),
        )
        raise err
    response = payload if isinstance(payload, dict) else {}
    cid = str(response.get("id") or response.get("conversation_id") or child_id)
    record_ledger(
        this_id,
        request_id,
        ledger_entry(
            operation="dispatch",
            request_id=request_id,
            ticket=ticket,
            department=department,
            parent_id=this_id,
            status="accepted",
            evidence=receipt["evidence"],
            child_id=cid,
            prompt_sha256=digest,
            profile_id=profile_id,
            working_dir=wd,
            attempts=attempts,
        ),
    )
    report = {
        **receipt,
        "id": cid,
        "conversation_id": cid,
        "url": f"{UI}/conversations/{cid}",
        "mode": "dispatch",
        "working_dir": wd,
        "this_id": this_id,
        "github_binding": binding_status(wants_binding),
        "evidence": receipt["evidence"],
        "next_action": (
            "accepted means API acceptance only, not department work "
            "completion; planning stops and does not watch"
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if args.poll_sec <= 0:
        return
    deadline = time.time() + args.timeout_sec
    last = None
    while time.time() < deadline:
        time.sleep(args.poll_sec)
        cur = get_conversation(cid) or {}
        last = status_of(cur)
        if last in TERMINAL_STATES:
            print(json.dumps({"id": cid, "status": last}, ensure_ascii=False), flush=True)
            if last != "finished":
                sys.exit(2)
            return
    raise SystemExit(f"poll timeout status={last!r}")


def resume_rejection(
    evidence: str,
    ctx: dict,
    ledger_parent: str,
    request_id: str,
    entry: dict | None,
) -> None:
    """Record and emit a rejected resume receipt, then fail closed.

    Args:
        evidence: Rejection evidence.
        ctx: Receipt context fields.
        ledger_parent: Ledger-owning conversation id.
        request_id: Logical request id.
        entry: Existing entry to preserve attempts from, if any.
    """
    receipt = make_receipt(
        "rejected", evidence=evidence, reconciled=False, **ctx
    )
    emit_receipt(receipt)
    attempts = int((entry or {}).get("attempts", 0))
    record_ledger(
        ledger_parent,
        request_id,
        ledger_entry(
            operation="resume",
            request_id=request_id,
            ticket=ctx.get("ticket", ""),
            department=ctx.get("department", ""),
            parent_id=ctx.get("parent_id", ""),
            status="rejected",
            evidence=evidence,
            target_id=ctx.get("target_id", ""),
            attempts=attempts,
        ),
    )


def reconcile_resume_entry(
    target_id: str, this_id: str, entry: dict, ctx: dict, state: str, text: str = ""
) -> str:
    """Reconcile an unknown resume receipt against the target lifecycle.

    Args:
        target_id: Conversation the continuation event was posted to.
        this_id: Parent conversation UUID (ledger key).
        entry: Prior resume ledger entry.
        ctx: Receipt context fields.
        state: Current lifecycle state of the target.
        text: Continuation text of the pending event, for the events-marker
            delivery check before the bounded re-send.

    Returns:
        "reconciled" when no re-send is needed, "resend" for the single
        bounded re-send.

    Raises:
        SystemExit: When the bounded attempt is exhausted or state unsafe.
    """
    attempts = int(entry.get("attempts", 0))
    if state == "running":
        emit_receipt(
            reconciled_receipt("unknown", "target is running", ctx)
        )
        updated = dict(entry)
        updated["status"] = "accepted"
        updated["evidence"] = "reconciled from unknown: target running"
        record_ledger(this_id, ctx["request_id"], updated)
        return "reconciled"
    if state in {"finished", "error"} and attempts < 2:
        if text and reconcile_event_marker(
            target_id, text, ctx, entry
        ) == "reconciled":
            return "reconciled"
        return "resend"
    emit_receipt(
        make_receipt(
            "unknown",
            evidence=(
                "bounded same-request re-send exhausted; delivery remains "
                "unproven"
            ),
            **ctx,
        )
    )
    raise SystemExit(1)


def run_resume(args: argparse.Namespace, parent: dict, this_id: str = "") -> None:
    """Resume the exact authorized direct-child department conversation.

    Args:
        args: Parsed CLI arguments.
        parent: This (parent) conversation payload.
        this_id: Canvas id of this conversation (defaults to parent id).
    """
    this_id = this_id or str(parent.get("id") or "")
    if parent.get("parent_conversation_id"):
        raise SystemExit(
            "resume rejected: caller must be a parentless planning root; "
            "planning must not resume as a child"
        )
    caller_tags = (
        parent.get("tags") if isinstance(parent.get("tags"), dict) else {}
    )
    caller_layer = str(caller_tags.get("layer") or "")
    caller_department = str(caller_tags.get("department") or "")
    # F2 (issue #24): only a parentless planning root may resume a child.
    # The caller's own layer/role is validated here, not just the target's.
    if caller_layer and caller_layer != "planning":
        raise SystemExit(
            "resume rejected: caller layer is not planning "
            f"(layer={caller_layer!r}); resume is planning-root -> direct child"
        )
    if caller_department and caller_department != "planning":
        raise SystemExit(
            "resume rejected: caller has a non-planning department tag "
            f"(department={caller_department!r}); resume is planning-root "
            "-> direct child"
        )
    ticket = normalize_ticket(args.ticket)
    request_id = normalize_request_id(args.request_id)
    target_id = args.target_id.strip()
    if not UUID_FORM.fullmatch(target_id):
        raise SystemExit(
            "--target-id must be the exact Agent Canvas conversation UUID "
            "of the original direct child; arbitrary target ids are rejected"
        )
    if not args.prompt_file:
        raise SystemExit("resume needs --prompt-file with the continuation text")
    text = Path(args.prompt_file).read_text(encoding="utf-8")
    wd = working_dir_of(parent)
    if not wd:
        raise SystemExit("this conversation has no workspace.working_dir")
    ledger = load_ledger(this_id)
    own = ledger.get(request_id)
    digest = prompt_digest(text)
    if own is not None and own.get("prompt_sha256") not in ("", digest):
        raise SystemExit(
            f"request identity collision: --request-id {request_id} was "
            "recorded with different resume text; fail-closed, use a new "
            "--request-id"
        )
    ctx = {
        "operation": "resume",
        "request_id": request_id,
        "ticket": ticket,
        "department": "",
        "parent_id": this_id,
        "target_id": target_id,
    }

    def reject(evidence: str, department: str = "") -> None:
        ctx["department"] = department
        resume_rejection(evidence, ctx, this_id, request_id, own)

    try:
        target = get_conversation(target_id)
    except (SystemExit, TimeoutError) as exc:
        message = str(exc)
        if isinstance(exc, TimeoutError) or "timed out" in message or "failed" in message:
            evidence = (
                f"resume target lookup for {target_id} timed out or response was lost; "
                "acceptance remains unknown and must be reconciled"
            )
            unknown = make_receipt("unknown", evidence=evidence, **ctx)
            emit_receipt(unknown)
            record_ledger(
                this_id,
                request_id,
                ledger_entry(
                    operation="resume",
                    request_id=request_id,
                    ticket=ticket,
                    department="",
                    parent_id=this_id,
                    status="unknown",
                    evidence=evidence,
                    target_id=target_id,
                    prompt_sha256=digest,
                    attempts=int((own or {}).get("attempts", 0)) + 1,
                ),
            )
        raise
    if target is None:
        reject(f"resume target {target_id} does not exist")
        raise SystemExit(f"resume target {target_id} does not exist")
    if str(target.get("parent_conversation_id") or "") != this_id:
        reject("resume target is not a direct child of this conversation")
        raise SystemExit(
            "resume target is not a direct child of this conversation; "
            "direction parent->own direct child is required"
        )
    tags = target.get("tags") if isinstance(target.get("tags"), dict) else {}
    if tags.get("clientsource") != "agentcanvas":
        reject("resume target is missing the Agent Canvas clientsource tag")
        raise SystemExit(
            "resume target is missing tags.clientsource=agentcanvas"
        )
    department = str(tags.get("department") or "")
    ctx["department"] = department
    if department not in AUTHORIZED_DEPARTMENTS:
        reject(f"resume target department {department!r} is not authorized", department)
        raise SystemExit(
            f"resume target has no authorized department tag: {department!r}"
        )
    if args.department and args.department != department:
        reject(f"resume target department {department} mismatches --department", department)
        raise SystemExit(
            f"department mismatch: target is {department}, --department "
            f"was {args.department}"
        )
    binding = next(
        (
            e
            for e in ledger.values()
            if e.get("operation") == "dispatch"
            and str(e.get("child_id") or "") == target_id
        ),
        None,
    )
    if binding is None:
        reject(
            "resume target is not bound in this conversation's ledger as an "
            "authorized department child (employee-layer bypass refused)",
            department,
        )
        raise SystemExit(
            f"resume target {target_id} is not bound in the dispatch ledger "
            "as an authorized department child of this conversation; "
            "employee-layer bypass is refused"
        )
    identity_mismatches = []
    if str(binding.get("child_id") or "") != target_id:
        identity_mismatches.append("target UUID")
    if str(binding.get("parent_id") or "") != this_id:
        identity_mismatches.append("parent UUID")
    if str(binding.get("department") or "") != department:
        identity_mismatches.append("department")
    if str(binding.get("ticket") or "") != ticket:
        identity_mismatches.append("ticket")
    if norm_path(str(binding.get("working_dir") or "")) != norm_path(wd):
        identity_mismatches.append("workspace")
    if identity_mismatches:
        evidence = (
            "resume target identity differs from its dispatch binding: "
            + ", ".join(identity_mismatches)
        )
        reject(evidence, department)
        raise SystemExit(evidence + "; fail-closed")
    if norm_path(working_dir_of(target) or "") != norm_path(wd):
        reject("resume target workspace differs from this conversation", department)
        raise SystemExit(
            "workspace mismatch: resume target working_dir differs from "
            "this conversation"
        )
    state = status_of(target)
    if own is not None and own.get("status") == "accepted":
        emit_receipt(
            reconciled_receipt("accepted", "prior resume event was accepted", ctx)
        )
        return
    if own is not None and own.get("status") == "unknown":
        if (
            reconcile_resume_entry(target_id, this_id, own, ctx, state, text)
            == "reconciled"
        ):
            return
        # single bounded re-send falls through
    elif state == "running":
        reject("active target; concurrent run refused", department)
        raise SystemExit(
            f"resume target {target_id} is active; concurrent run refused"
        )
    elif state == "stopped":
        reject("stopped target; no silent success, no recreate", department)
        raise SystemExit(
            f"resume target {target_id} is stopped; no silent success and "
            "no recreate"
        )
    elif state == "error":
        if int((own or {}).get("attempts", 0)) >= 1:
            reject(
                "bounded resume attempt for an error target already used",
                department,
            )
            raise SystemExit(
                f"resume target {target_id} is in error and its single "
                "bounded resume attempt was already used"
            )
    elif state != "finished":
        reject(f"unrecognized lifecycle state {state!r}", department)
        raise SystemExit(
            f"resume target {target_id} has unrecognized lifecycle state "
            f"{state!r}; refusing to act"
        )
    payload, receipt, err = send_event(
        target_id,
        text,
        lambda method, path, body, emit: http_op(
            method,
            path,
            body,
            timeout=EVENT_POST_TIMEOUT,
            operation="resume",
            request_id=request_id,
            ticket=ticket,
            department=department,
            parent_id=this_id,
            target_id=target_id,
            emit=emit,
        ),
        ctx,
    )
    attempts = int((own or {}).get("attempts", 0)) + 1
    if err is not None:
        record_ledger(
            this_id,
            request_id,
            ledger_entry(
                operation="resume",
                request_id=request_id,
                ticket=ticket,
                department=department,
                parent_id=this_id,
                status=receipt["receipt"],
                evidence=receipt["evidence"],
                target_id=target_id,
                prompt_sha256=digest,
                attempts=attempts,
            ),
        )
        raise err
    record_ledger(
        this_id,
        request_id,
        ledger_entry(
            operation="resume",
            request_id=request_id,
            ticket=ticket,
            department=department,
            parent_id=this_id,
            status="accepted",
            evidence=receipt["evidence"],
            target_id=target_id,
            prompt_sha256=digest,
            attempts=attempts,
        ),
    )
    report = {
        "receipt": "accepted",
        "operation": "resume",
        "request_id": request_id,
        "ticket": ticket,
        "department": department,
        "target_id": target_id,
        "parent_id": this_id,
        "url": f"{UI}/conversations/{target_id}",
        "evidence": receipt["evidence"],
        "next_action": (
            "continuation event accepted on the original department child; "
            "accepted is not work completion; planning stops and does not "
            "watch"
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


def run_notify(args: argparse.Namespace, parent: dict, this_id: str = "") -> None:
    """Notify the parent planning conversation, child->parent only.

    Args:
        args: Parsed CLI arguments.
        parent: This (department) conversation payload.
        this_id: Canvas id of this conversation (defaults to parent id).
    """
    this_id = this_id or str(parent.get("id") or "")
    parent_id = parent.get("parent_conversation_id")
    if not parent_id:
        raise SystemExit("notify needs parent_conversation_id. Planning must not notify.")
    if not args.prompt_file:
        raise SystemExit("notify needs --prompt-file")
    text = Path(args.prompt_file).read_text(encoding="utf-8")
    if not text.lstrip().startswith(REPORT_PREFIX):
        raise SystemExit("notify prompt must start with engineering:report")
    tags = parent.get("tags") if isinstance(parent.get("tags"), dict) else {}
    layer = str(tags.get("layer") or "")
    department = str(tags.get("department") or "")
    # F1 (issue #24): only a department-layer child may hop a report to its
    # parent. A caller that is not marked as a department child (or whose
    # department tag is not a non-planning department) must not reach the
    # parent event POST, whatever its stored conversation id is.
    if layer != "department" or not department or department == "planning":
        raise SystemExit(
            "notify rejected: caller is not a department-layer child "
            f"(layer={layer!r}, department={department!r}); "
            "notify is child->parent only"
        )
    request_id = (
        normalize_request_id(args.request_id) if args.request_id.strip() else str(uuid.uuid4())
    )
    report_digest = prompt_digest(text)
    request_match = re.search(r"^\s*request:\s*(\S+)\s*$", text, re.M)
    report_request = request_match.group(1) if request_match else ""
    ticket_match = re.search(r"^\s*ticket:\s*(#\d+)\s*$", text, re.M)
    ticket = args.ticket.strip() or (ticket_match.group(1) if ticket_match else "")
    related = args.related_request_id.strip() or report_request
    target_id = str(parent_id)
    ledger = load_ledger(target_id)
    correlation = ""
    if report_request:
        if not related or report_request != related:
            raise SystemExit(
                f"notify rejected as stale/mismatched: report must contain a "
                f"`request: {related}` line equal to --related-request-id"
            )
        related_entry = ledger.get(related)
        related_known = (
            isinstance(related_entry, dict)
            and related_entry.get("operation") in {"dispatch", "resume"}
            and (
                str(related_entry.get("child_id") or related_entry.get("target_id") or "")
                == this_id
            )
            and str(related_entry.get("ticket") or "") == ticket
            and str(related_entry.get("parent_id") or "") == target_id
        )
        if not related_known:
            raise SystemExit(
                f"notify rejected as stale/mismatched: related request {related!r} "
                "is not a known dispatch/resume request for this child and ticket"
            )
    else:
        # Carried correlated-session path (#24): the report carries its own
        # correlation tags; only a legacy report may pass unverified.
        related = args.related_request_id.strip()
        if related:
            raise SystemExit(
                f"notify rejected as stale/mismatched: report must contain a "
                f"`request: {related}` line equal to --related-request-id"
            )
        correlation = validate_report(text, parent, args.allow_legacy_report)
        if correlation == "legacy-unverified":
            text = (
                f"{text.rstrip()}\n"
                "correlation: legacy-unverified\n"
                "completion-eligible: false\n"
            )
    digest = report_digest
    own = ledger.get(request_id)
    ctx = {
        "operation": "notify",
        "request_id": request_id,
        "ticket": ticket,
        "department": str(
            (parent.get("tags") or {}).get("department", "")
            if isinstance(parent.get("tags"), dict)
            else ""
        ),
        "parent_id": target_id,
        "target_id": target_id,
    }
    if own is not None:
        if own.get("prompt_sha256") not in ("", digest):
            raise SystemExit(
                f"request identity collision: --request-id {request_id} was "
                "recorded with different report text; fail-closed, use a new "
                "--request-id"
            )
        if own.get("status") == "rejected":
            raise SystemExit(
                f"request {request_id} was previously rejected; do not retry "
                "unchanged"
            )
        if own.get("status") == "accepted":
            emit_receipt(reconciled_receipt("accepted", "identical replay", ctx))
            return
        if own.get("status") == "unknown":
            # Reconcile before the bounded re-send (#51): a lost response
            # may have still persisted; never duplicate a delivered report.
            # This runs before the attempts gate so a proven delivery
            # reconciles even at exhaustion (dedup beats the bound).
            if (
                reconcile_event_marker(target_id, text, ctx, own)
                == "reconciled"
            ):
                return
        if int(own.get("attempts", 0)) >= 2:
            emit_receipt(
                make_receipt(
                    "unknown",
                    evidence="bounded same-request re-send exhausted",
                    **ctx,
                )
            )
            raise SystemExit(1)
        # single bounded re-send falls through
    payload, receipt, err = send_event(
        target_id,
        text,
        lambda method, path, body, emit: http_op(
            method,
            path,
            body,
            timeout=EVENT_POST_TIMEOUT,
            operation="notify",
            request_id=request_id,
            ticket=ticket,
            department=ctx["department"],
            parent_id=target_id,
            target_id=target_id,
            emit=emit,
        ),
        ctx,
    )
    attempts = int((own or {}).get("attempts", 0)) + 1
    if err is not None:
        record_ledger(
            target_id,
            request_id,
            ledger_entry(
                operation="notify",
                request_id=request_id,
                ticket=ticket,
                department=ctx["department"],
                parent_id=target_id,
                status=receipt["receipt"],
                evidence=receipt["evidence"],
                target_id=target_id,
                prompt_sha256=digest,
                attempts=attempts,
            ),
        )
        raise err
    record_ledger(
        target_id,
        request_id,
        ledger_entry(
            operation="notify",
            request_id=request_id,
            ticket=ticket,
            department=ctx["department"],
            parent_id=target_id,
            status="accepted",
            evidence=receipt["evidence"],
            target_id=target_id,
            prompt_sha256=digest,
            attempts=attempts,
        ),
    )
    report = {
        **receipt,
        "mode": "notify",
        "this_id": this_id,
        "parent_id": target_id,
        "url": f"{UI}/conversations/{target_id}",
        "posted": payload if isinstance(payload, dict) else True,
        "correlation": correlation,
        "completion_eligible": correlation == "exact",
        "evidence": receipt["evidence"],
        "next_action": (
            "accepted means the report post was accepted, not that the hop "
            "is done; a lost response is unknown until reconciled"
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


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
    checked = get_conversation(cid, timeout=180)
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


def validate_persisted_dispatch(
    child: dict,
    child_id: str,
    parent_id: str,
    dispatch_id: str,
    department: str,
    ticket: str,
) -> None:
    """Verify that a department dispatch persisted its correlation identity.

    Args:
        child: Persisted child payload returned by a follow-up GET.
        child_id: Created child conversation id.
        parent_id: Dispatching planning conversation id.
        dispatch_id: Expected dispatch UUID.
        department: Expected department tag.
        ticket: Expected ticket tag.
    """
    tags = child.get("tags") if isinstance(child.get("tags"), dict) else {}
    expected = {
        "child conversation id": (child.get("id"), child_id),
        "parent conversation id": (child.get("parent_conversation_id"), parent_id),
        "dispatch id": (tags.get("dispatch_id"), dispatch_id),
        "department": (tags.get("department"), department),
        "ticket": (tags.get("ticket"), ticket),
    }
    mismatches = [
        key for key, (actual, wanted) in expected.items() if str(actual or "") != wanted
    ]
    if mismatches:
        details = ", ".join(mismatches)
        raise SystemExit(f"persisted dispatch metadata mismatch: {details}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create, resume, or notify an Agent Canvas conversation. Never prints the API key.",
        epilog=PROFILE_HINT,
    )
    parser.add_argument(
        "--mode",
        choices=("open", "dispatch", "resume", "this", "notify"),
        required=True,
    )
    parser.add_argument("--this-id", default="", help="Canvas GET id. Not CURSOR_CONVERSATION_ID. Omit to resolve.")
    parser.add_argument("--profile-id", default="", help=PROFILE_ID_HELP)
    parser.add_argument("--github-token-secret", default="")
    parser.add_argument("--prompt-file", default="")
    parser.add_argument(
        "--department",
        default="",
        choices=sorted(DEPARTMENTS - {"planning"}),
        help="department scope of the dispatch target",
    )
    parser.add_argument(
        "--ticket",
        default="",
        help="ticket scope of the dispatch/resume identity, e.g. #41",
    )
    parser.add_argument(
        "--request-id",
        default="",
        help="logical request id (uuid/hex) scoping one intentional request",
    )
    parser.add_argument(
        "--target-id",
        default="",
        help="resume: exact direct-child conversation UUID to resume",
    )
    parser.add_argument(
        "--related-request-id",
        default="",
        help="notify: require a matching `request: <id>` line in the report",
    )
    parser.add_argument(
        "--dispatch-id",
        default="",
        help="legacy dispatch correlation id (correlation tags)",
    )
    parser.add_argument("--allow-legacy-report", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=500)
    parser.add_argument("--poll-sec", type=int, default=0)
    parser.add_argument("--timeout-sec", type=int, default=5400)
    parser.add_argument(
        "--force", action="store_true", help="allow an active duplicate dispatch"
    )
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
        terminal = prior_state in TERMINAL_STATES
        posted = post_message(args.target_id, text, run=not terminal)
        if terminal:
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
                    "resume_behavior": (
                        "message-then-run" if terminal else "message-with-run"
                    ),
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
        run_notify(args, parent)
        return

    if args.mode == "resume":
        run_resume(args, parent)
        return

    if args.mode == "dispatch":
        run_dispatch(args, parent)
        return

    if not args.profile_id or not args.prompt_file:
        raise SystemExit("open needs --profile-id and --prompt-file")
    validate_profile_id(args.profile_id)
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    wd = working_dir_of(parent)
    if not wd:
        raise SystemExit("this conversation has no workspace.working_dir")
    why = refuse_path(wd)
    if why:
        raise SystemExit(f"refuse this conversation working_dir {wd!r}: {why}")

    wants_binding = bool(args.department or args.github_token_secret)
    if bool(args.department) != bool(args.github_token_secret):
        raise SystemExit(
            "GitHub binding requires both --department and --github-token-secret"
        )
    secrets = None
    if wants_binding:
        key = session_key()
        probe_secret_source(args.github_token_secret, key)
        secrets = github_binding(args.github_token_secret, key)
        prompt = bound_department_prompt(prompt)

    tags = canvas_tags(parent)
    child_id = str(uuid.uuid4())
    if args.department:
        tags["department"] = args.department
        if args.mode == "dispatch":
            refuse_duplicate_dispatch(this_id, tags, args.force)
            if not args.force:
                child_id = dispatch_child_id(this_id, args.department)
    if wants_binding:
        tags["githubbinding"] = "gh-token-bound"
    body = conversation_body(
        child_id=child_id,
        profile_id=args.profile_id,
        working_dir=wd,
        prompt=prompt,
        tags=tags,
        max_iterations=args.max_iterations,
        parent_id=this_id if args.mode == "dispatch" else None,
        secrets=secrets,
    )

    created = api(
        "POST",
        "/api/conversations",
        body,
        timeout=180,
        redact_error=wants_binding,
    )
    if not isinstance(created, dict):
        detail = " (details redacted)" if wants_binding else f": {created!r}"
        raise SystemExit(f"unexpected create payload{detail}")
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
        "department": args.department,
        "ticket": args.ticket or None,
        "working_dir": got,
        "tags": checked.get("tags") if isinstance(checked.get("tags"), dict) else {},
        "parent_conversation_id": checked.get("parent_conversation_id"),
        "max_iterations": args.max_iterations,
        "launched_agent_profile": checked.get("launched_agent_profile"),
        "this_id": this_id,
        "github_binding": binding_status(wants_binding),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)

    if args.poll_sec <= 0:
        if wants_binding:
            ledger_mark_completed(this_id, request_id)
        return
    terminal = {"finished", "error", "stopped"}
    deadline = time.time() + args.timeout_sec
    last = None
    while time.time() < deadline:
        time.sleep(args.poll_sec)
        cur = get_conversation(cid, timeout=180) or {}
        last = status_of(cur)
        if last in terminal:
            print(json.dumps({"id": cid, "status": last}, ensure_ascii=False), flush=True)
            if last != "finished":
                sys.exit(2)
            if wants_binding:
                ledger_mark_completed(this_id, request_id)
            return
    raise SystemExit(f"poll timeout status={last!r}")


if __name__ == "__main__":
    main()
