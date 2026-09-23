"""Resume seam for Agent Canvas sessions."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from . import identity, ledger, notify, transport
from .identity import (
    normalize_request_id,
    normalize_ticket,
    norm_path,
    status_of,
    working_dir_of,
    DEPARTMENTS,
)
from .ledger import (
    emit_receipt,
    http_op,
    ledger_entry,
    load_ledger,
    make_receipt,
    prompt_digest,
    reconcile_resume_entry,
    reconciled_receipt,
    record_ledger,
    resume_rejection,
)

NON_TERMINAL_RESUMABLE_STATES = {"awaiting_input", "paused", "idle"}
RESUMABLE_STATES = identity.TERMINAL_STATES | NON_TERMINAL_RESUMABLE_STATES


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
            return transport.api("POST", f"/api/conversations/{cid}/events", body)
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
    # F2 (issue #24): the caller's own layer/role must be a parentless
    # planning root, not merely a conversation without a parent pointer.
    caller_tags = (
        parent.get("tags") if isinstance(parent.get("tags"), dict) else {}
    )
    caller_layer = str(caller_tags.get("layer") or "")
    caller_department = str(caller_tags.get("department") or "")
    if caller_layer and caller_layer != "planning":
        raise SystemExit(
            "resume rejected: caller layer is not planning "
            f"(layer={caller_layer!r}); resume is planning-root -> direct child"
        )
    if caller_department and caller_department != "planning":
        raise SystemExit(
            "resume rejected: caller has a non-planning department tag "
            f"(department={caller_department!r}); resume is planning-root -> "
            "direct child"
        )
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
    if not identity.UUID_FORM.fullmatch(target_id):
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
    ledger_map = load_ledger(this_id)
    own = ledger_map.get(request_id)
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
        target = transport.get_conversation(target_id)
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
    if department not in identity.AUTHORIZED_DEPARTMENTS:
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
            for e in ledger_map.values()
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
    elif state in NON_TERMINAL_RESUMABLE_STATES:
        # Role-form continuation (run=true) resumes a paused/idle child too;
        # no separate run call is needed.
        pass
    elif state != "finished":
        reject(f"unrecognized lifecycle state {state!r}", department)
        raise SystemExit(
            f"resume target {target_id} has unrecognized lifecycle state "
            f"{state!r}; refusing to act"
        )
    payload, receipt, err = notify.send_event(
        target_id,
        text,
        lambda method, path, body, emit: http_op(
            method,
            path,
            body,
            timeout=transport.EVENT_POST_TIMEOUT,
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
        "url": f"{transport.UI}/conversations/{target_id}",
        "resume_behavior": "message-with-run",
        "evidence": receipt["evidence"],
        "next_action": (
            "continuation event accepted on the original department child; "
            "accepted is not work completion; planning stops and does not "
            "watch"
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
