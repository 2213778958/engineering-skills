"""Receipt, ledger, and reconciliation seam for Agent Canvas sessions."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import datetime
from pathlib import Path
from typing import Any

from . import notify, transport
from . import identity as identity_module


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
    if not identity_module.UUID_FORM.fullmatch(parent_id.strip()):
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
        "identity": identity or identity_module.request_identity(parent_id, department, ticket, request_id),
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
        payload = transport.api(method, path, body, timeout=timeout, redact_error=redact_error)
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
    for item in identity_module.search_items():
        if str(item.get("parent_conversation_id") or "") != parent_id:
            continue
        item_tags = item.get("tags") if isinstance(item.get("tags"), dict) else {}
        if str(item_tags.get("department") or "") != department:
            continue
        if identity_module.status_of(item) not in terminal:
            duplicates.append(item)
    if duplicates:
        details = ", ".join(
            f"{item.get('id')} ({transport.UI}/conversations/{item.get('id')})"
            for item in duplicates
        )
        raise SystemExit(
            f"active {department} dispatch already exists: {details}; use --force to bypass"
        )


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
    marker = notify.event_marker(text)
    found = bool(marker) and any(
        marker in blob for blob in notify.target_event_texts(target_id)
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
        child = transport.get_conversation(str(entry.get("child_id") or ""))
        if child is not None and identity_module.status_of(child) not in identity_module.TERMINAL_STATES:
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
    if identity_module.norm_path(str(entry.get("working_dir") or "")) != identity_module.norm_path(wd):
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
    child = transport.get_conversation(child_ref)
    state = identity_module.status_of(child)
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
