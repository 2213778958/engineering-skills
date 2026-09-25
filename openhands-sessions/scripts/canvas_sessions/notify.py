"""Report validation and event notification seam for Agent Canvas sessions."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from . import identity, transport
import canvas_sessions.ledger as ledger
from .identity import DEPARTMENTS

REPORT_PREFIX = "engineering:report"
DELIVERY_MARKER_PREFIX = "delivery-marker"
REPORT_HOPS = {
    "done",
    "send-back",
    "need-arbitration",
    "need-human",
    "blocked",
    "wait-merge",
}


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


def embed_delivery_marker(text: str) -> str:
    """Append a short unique uuid sentinel to the delivery text.

    The backend may accept an event POST (HTTP 202) yet persist it with
    empty content (#49/#56). API acceptance alone therefore proves nothing;
    the sentinel gives the post-POST readback an exact, per-delivery token
    to demand from the persisted user message, so a stale or sibling event
    can never pass for this delivery.

    Args:
        text: Report or continuation text about to be posted.

    Returns:
        The text with a ``delivery-marker: <short-uuid>`` line appended;
        unchanged when a marker line is already present.
    """
    if DELIVERY_MARKER_PREFIX in text:
        return text
    token = uuid.uuid4().hex[:12]
    return f"{text.rstrip()}\n{DELIVERY_MARKER_PREFIX}: {token}"


def delivery_sentinel(text: str) -> str:
    """Extract the sentinel token this delivery must read back.

    Args:
        text: Delivery text after embed_delivery_marker.

    Returns:
        The ``delivery-marker`` value, or the stripped text when no marker
        line is present (legacy callers).
    """
    match = re.search(
        rf"^\s*{re.escape(DELIVERY_MARKER_PREFIX)}:\s*(\S+)\s*$", text, re.M
    )
    return match.group(1) if match else text.strip()


def is_user_message_event(event: object) -> bool:
    """Classify one persisted event as a user MessageEvent.

    Args:
        event: One item from the events search response.

    Returns:
        True when the item is a MessageEvent raised by the user side (the
        role-style POST is persisted under the MessageEvent kind).
    """
    if not isinstance(event, dict):
        return False
    kind = str(event.get("kind") or "")
    if kind and kind != "MessageEvent":
        return False
    source = str(event.get("source") or "")
    if source and source != "user":
        return False
    llm_message = event.get("llm_message")
    role = ""
    if isinstance(llm_message, dict):
        role = str(llm_message.get("role") or "")
    return role == "user" or str(event.get("role") or "") == "user"


def readback_delivery_text(cid: str) -> str | None:
    """Read the newest persisted user MessageEvent text for one conversation.

    Uses the same conversation-scoped events search endpoint as the
    reconcile read (#53), newest first.

    Args:
        cid: Conversation whose persisted events are read.

    Returns:
        The flattened text of the newest user MessageEvent (empty string
        when it carries no text), or None when the read fails outright or
        no user MessageEvent exists. Both failure shapes must be judged a
        delivery failure by the caller (#56).
    """
    try:
        payload = transport.api("GET", event_search_path(cid))
    except (SystemExit, TimeoutError, *ledger.TRANSPORT_ERRORS):
        return None
    items: list[object] = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    for event in items:
        if not is_user_message_event(event):
            continue
        llm_message = event.get("llm_message")
        if isinstance(llm_message, dict):
            return event_text_blob(llm_message)
        return event_text_blob(event)
    return None


def send_event(
    cid: str, text: str, poster, ctx: dict
) -> tuple[object, dict, BaseException | None]:
    """POST the continuation/report event and prove it persisted (#56).

    The POST is delivered with the role-style payload plus an embedded
    delivery sentinel. API acceptance is not proof (#49: HTTP 202 with
    empty persisted content), so the newest persisted user MessageEvent is
    read back and must be non-empty and contain the sentinel. Any readback
    failure is a transport-level unknown: the caller records it through the
    existing ledger and the bounded re-send path, never as accepted.

    Args:
        cid: Target conversation (parent for notify, exact child for resume).
        text: Report or continuation text.
        poster: Callable (method, path, body, emit) -> (payload, receipt, err).
        ctx: Receipt context (operation/request_id/ticket/department/...).

    Returns:
        (payload, receipt, error) of the delivery. error is None only when
        the POST was accepted AND the readback proves the sentinel landed.
    """
    delivery_text = embed_delivery_marker(text)
    sentinel = delivery_sentinel(delivery_text)
    payload, receipt, err = poster(
        "POST",
        f"/api/conversations/{cid}/events",
        event_payload(delivery_text),
        True,
    )
    if err is not None:
        return payload, receipt, err
    persisted = readback_delivery_text(cid)
    if persisted is None:
        evidence = (
            f"delivery readback failed: newest user MessageEvent for "
            f"{cid} not found or events read failed; acceptance unproven"
        )
    elif not persisted.strip():
        evidence = (
            f"delivery readback failed: newest user MessageEvent for "
            f"{cid} persisted with empty content; text was lost (#49)"
        )
    elif sentinel not in persisted:
        evidence = (
            f"delivery readback failed: sentinel {sentinel!r} missing from "
            f"newest user MessageEvent for {cid}; acceptance unproven"
        )
    else:
        return payload, receipt, None
    unknown = ledger.make_receipt("unknown", evidence=evidence, **ctx)
    ledger.emit_receipt(unknown)
    return None, unknown, SystemExit(evidence)


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


def event_search_path(cid: str) -> str:
    """Build the conversation-scoped events-search path and query.

    The bare ``GET /api/conversations/{id}/events`` form is rejected by the
    server (422); events are read back through the search endpoint with the
    conversation id in the path, newest first (same shape the watch adapter
    uses).

    Args:
        cid: Conversation whose persisted events are read.

    Returns:
        Path plus query string for the events search endpoint.
    """
    qs = urlencode({"limit": 100, "sort_order": "TIMESTAMP_DESC"})
    return f"/api/conversations/{cid}/events/search?{qs}"


def target_event_texts(cid: str) -> list[str]:
    """Read the target conversation's recent events as text blobs.

    Args:
        cid: Conversation whose persisted events are read.

    Returns:
        One text blob per event, best-effort. An unreadable events endpoint
        (missing, rejected, timed out, connection lost) yields an empty list
        so callers treat delivery as unproven and keep the bounded re-send
        as the fallback instead of aborting the reconcile.
    """
    try:
        payload = transport.api("GET", event_search_path(cid))
    except (SystemExit, TimeoutError, *ledger.TRANSPORT_ERRORS):
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


def run_notify(args: argparse.Namespace, parent: dict, this_id: str = "") -> None:
    """Notify the parent planning conversation, child->parent only.

    Issue #53: when ``--parent-id`` (or OPENHANDS_PARENT_CONVERSATION_ID) is
    given, it is cross-checked against this conversation's persisted
    ``parent_conversation_id`` before any lookup or POST; a mismatch exits
    non-zero so a mis-attributed report can never land on a guessed parent.

    Args:
        args: Parsed CLI arguments.
        parent: This (department) conversation payload.
        this_id: Canvas id of this conversation (defaults to parent id).
    """
    this_id = this_id or str(parent.get("id") or "")
    parent_id = parent.get("parent_conversation_id")
    if not parent_id:
        raise SystemExit("notify needs parent_conversation_id. Planning must not notify.")
    expected_parent = str(getattr(args, "parent_id", "") or "").strip()
    if expected_parent and expected_parent != str(parent_id):
        raise SystemExit(
            f"notify rejected: --parent-id {expected_parent!r} does not match "
            f"this conversation's parent {parent_id!r}; fail-closed, never "
            "post to a guessed parent"
        )
    if not args.prompt_file:
        raise SystemExit("notify needs --prompt-file")
    text = Path(args.prompt_file).read_text(encoding="utf-8")
    if not text.lstrip().startswith(REPORT_PREFIX):
        raise SystemExit("notify prompt must start with engineering:report")
    tags = parent.get("tags") if isinstance(parent.get("tags"), dict) else {}
    layer = str(tags.get("layer") or "")
    department = str(tags.get("department") or "")
    # F1 (issue #24): only a department-layer child may hop a report to its
    # parent. The child identity is either the explicit #24 layer tag or,
    # for new-main dispatches that never wrote a layer tag, the structural
    # child shape (the parent pointer is already required above plus
    # clientsource=agentcanvas plus an authorized non-planning department).
    # An explicit non-department layer (employee window) and planning
    # departments are rejected here, before any POST.
    if layer and layer != "department":
        raise SystemExit(
            "notify rejected: caller layer is not a department child "
            f"(layer={layer!r}, department={department!r}); "
            "notify is child->parent only"
        )
    if not department or department == "planning":
        raise SystemExit(
            "notify rejected: caller is not a department-layer child "
            f"(layer={layer!r}, department={department!r}); "
            "notify is child->parent only"
        )
    if not layer and (
        str(tags.get("clientsource") or "") != "agentcanvas"
        or department not in identity.AUTHORIZED_DEPARTMENTS
    ):
        raise SystemExit(
            "notify rejected: caller is not a department-layer child "
            f"(layer={layer!r}, department={department!r}); "
            "notify is child->parent only"
        )
    request_id = (
        identity.normalize_request_id(args.request_id) if args.request_id.strip() else str(uuid.uuid4())
    )
    report_digest = ledger.prompt_digest(text)
    request_match = re.search(r"^\s*request:\s*(\S+)\s*$", text, re.M)
    report_request = request_match.group(1) if request_match else ""
    ticket_match = re.search(r"^\s*ticket:\s*(#\d+)\s*$", text, re.M)
    ticket = args.ticket.strip() or (ticket_match.group(1) if ticket_match else "")
    related = args.related_request_id.strip() or report_request
    target_id = str(parent_id)
    ledger_map = ledger.load_ledger(target_id)
    correlation = ""
    if report_request:
        if not related or report_request != related:
            raise SystemExit(
                f"notify rejected as stale/mismatched: report must contain a "
                f"`request: {related}` line equal to --related-request-id"
            )
        related_entry = ledger_map.get(related)
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
    own = ledger_map.get(request_id)
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
            ledger.emit_receipt(ledger.reconciled_receipt("accepted", "identical replay", ctx))
            return
        if own.get("status") == "unknown":
            # Reconcile before the bounded re-send (#51): a lost response
            # may have still persisted; never duplicate a delivered report.
            # This runs before the attempts gate so a proven delivery
            # reconciles even at exhaustion (dedup beats the bound).
            if (
                ledger.reconcile_event_marker(target_id, text, ctx, own)
                == "reconciled"
            ):
                return
        if int(own.get("attempts", 0)) >= 2:
            ledger.emit_receipt(
                ledger.make_receipt(
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
        lambda method, path, body, emit: ledger.http_op(
            method,
            path,
            body,
            timeout=transport.EVENT_POST_TIMEOUT,
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
        ledger.record_ledger(
            target_id,
            request_id,
            ledger.ledger_entry(
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
    ledger.record_ledger(
        target_id,
        request_id,
        ledger.ledger_entry(
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
        "url": f"{transport.UI}/conversations/{target_id}",
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
