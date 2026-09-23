from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = os.environ.get("OPENHANDS_URL", "http://localhost:8000").rstrip("/")
KEY_PATH = Path.home() / ".openhands" / "agent-canvas" / "api-key.txt"
UI = os.environ.get("OPENHANDS_UI", "http://localhost:3001").rstrip("/")

SECRET_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
GITHUB_CONSUMER = "GH_TOKEN"
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


def maybe_run(cid: str) -> None:
    try:
        api("POST", f"/api/conversations/{cid}/run", {})
    except SystemExit:
        return


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

