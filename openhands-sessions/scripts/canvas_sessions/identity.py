from __future__ import annotations

import os
import re
import uuid
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from . import transport

UUID_FORM = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
WT_SEGMENT = re.compile(r"(?:^|[\\/])worktree(?:[\\/]|$)", re.I)
SIBLING_TREE = re.compile(r"-wt(?:-pr)?-\d+|[-_/]iso-\d+", re.I)
AUTHORIZED_DEPARTMENTS = ("delivery", "acceptance", "arbitration", "human")
TICKET_FORM = re.compile(r"^#\d+$")
REQUEST_FORM = re.compile(r"^[0-9a-zA-Z][0-9a-zA-Z-]{7,63}$")
TERMINAL_STATES = {"finished", "error", "stopped"}
DEPARTMENTS = {"delivery", "acceptance", "arbitration", "human", "planning"}
PROFILE_HINT = (
    "--profile-id takes the Agent Canvas profile UUID, not the human-readable "
    "profile name. Discover it from the agent-profile catalog "
    "(GET /api/agent-profiles, response key 'profiles', field 'id'), "
        "e.g. 123e4567-e89b-12d3-a456-426614174000."
)


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
        payload = transport.api("GET", f"/api/conversations/search?{urlencode(params)}")
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


def workspace_candidates(items: list[dict[str, Any]], want: str) -> list[str]:
    """Return every conversation id whose workspace matches a normalized dir.

    Args:
        items: Conversation records from a search.
        want: Normalized (``norm_path``) working_dir to match.

    Returns:
        All matching ids in the caller-provided order. The caller decides
        what to do with more than one candidate; this function never picks
        one, because most-recently-updated is not a safe disambiguator under
        parallel same-working_dir conversations.
    """
    return [str(x["id"]) for x in items if is_workspace_hit(x, want)]


def pick_workspace_id(items: list[dict[str, Any]], want: str) -> str | None:
    """Resolve one workspace-matching id, failing closed on ambiguity.

    Args:
        items: Conversation records from a search.
        want: Normalized (``norm_path``) working_dir to match.

    Returns:
        The single matching id, or None when none matches.

    Raises:
        SystemExit: When several conversations match the same working_dir;
            silently picking the most recently updated would deterministically
            resolve the wrong conversation under parallel same-dir runs.
    """
    hits = workspace_candidates(items, want)
    if not hits:
        return None
    if len(hits) > 1:
        raise SystemExit(
            "workspace identity is ambiguous: "
            f"{len(hits)} conversations share working_dir {want!r}: "
            + ", ".join(hits)
            + "; pass --this-id or OPENHANDS_CONVERSATION_ID explicitly"
        )
    return hits[0]


def resolve_this(explicit: str | None) -> str:
    """Resolve the Canvas conversation id of the caller, fail-closed.

    Resolution order: explicit ``--this-id``, then the conversation-id
    environment, then the same-working_dir heuristic. Explicit and
    environment values must resolve through the API; a missing conversation
    is an error, never a fallthrough into the heuristic. The heuristic is
    read-only mode support only and refuses multiple candidates instead of
    silently picking one.

    Args:
        explicit: ``--this-id`` value, or None when omitted.

    Returns:
        The resolved Canvas conversation id.

    Raises:
        SystemExit: When an explicit id or env id does not exist, when the
            heuristic has multiple candidates, or when nothing matches.
    """
    if explicit:
        conv = transport.get_conversation(explicit)
        if conv and conv.get("id"):
            return str(conv["id"])
        raise SystemExit(
            f"--this-id {explicit!r} did not resolve to a Canvas conversation "
            "(a 404 means it is not a Canvas GET id); do not fall back to "
            "the working_dir heuristic"
        ) from None
    for key in ("OPENHANDS_CONVERSATION_ID", "CONVERSATION_ID"):
        val = os.environ.get(key, "").strip()
        if not val:
            continue
        conv = transport.get_conversation(val)
        if conv and conv.get("id"):
            return str(conv["id"])
        raise SystemExit(
            f"{key}={val!r} did not resolve to a Canvas conversation "
            "(a 404 means it is not a Canvas GET id); do not fall back to "
            "the working_dir heuristic"
        ) from None
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


def require_explicit_this(explicit: str | None, mode: str) -> None:
    """Reject mutating modes that would rely on heuristic identity resolution.

    Issue #53: dispatch and notify write into another conversation, so a
    silently-resolved (same-working_dir, most-recent) identity can act on the
    previous parallel conversation. These modes require an explicit
    ``--this-id`` or ``OPENHANDS_CONVERSATION_ID``; the heuristic fallback is
    reserved for read-only modes.

    Args:
        explicit: The explicitly provided id (flag or env), or None/empty.
        mode: The CLI mode requesting resolution (for the error message).
    """
    if not explicit:
        raise SystemExit(
            f"{mode} requires an explicit conversation id: pass --this-id or "
            "set OPENHANDS_CONVERSATION_ID; the same-working_dir heuristic "
            "is ambiguous under parallel same-dir conversations and is "
            "refused for mutating modes (fail-closed)"
        )
