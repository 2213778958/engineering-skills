"""Dispatch seam for Agent Canvas sessions."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from . import identity, ledger, transport
from .ledger import load_ledger

__all__ = [
    "bound_department_prompt",
    "conversation_body",
    "run_dispatch",
    "validate_persisted_dispatch",
]


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
    env: dict[str, str] | None = None,
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
        env: Explicit child environment (no implicit os.environ inheritance).

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
    if env:
        body["env"] = env
    return body


def run_dispatch(args: argparse.Namespace, parent: dict, this_id: str = "") -> None:
    """Dispatch a department child under a request-scoped identity.

    Issue #53: the dispatching conversation is bound explicitly — main()
    refuses dispatch without ``--this-id``/env — and this seam injects the
    resolved identity into the child: the child id is set as
    ``OPENHANDS_CONVERSATION_ID`` in the child environment (all runs) and
    mirrored into a ``conversation_id`` tag when absent, so the child's own
    sessions modes and its notify parent cross-check never fall back to the
    ambiguous same-working_dir heuristic.

    Args:
        args: Parsed CLI arguments.
        parent: This (planning) conversation payload.
        this_id: Canvas id of this conversation (defaults to parent id).
    """
    this_id = this_id or str(parent.get("id") or "")
    department = args.department or ""
    if not department:
        raise SystemExit("dispatch needs --department")
    profile_id = identity.validate_profile_id(args.profile_id)
    if not profile_id:
        raise SystemExit("dispatch needs --profile-id")
    ticket = identity.normalize_ticket(args.ticket)
    request_id = identity.normalize_request_id(args.request_id)
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    wd = identity.working_dir_of(parent)
    if not wd:
        raise SystemExit("this conversation has no workspace.working_dir")
    why = identity.refuse_path(wd)
    if why:
        raise SystemExit(f"refuse this conversation working_dir {wd!r}: {why}")
    wants_binding = bool(args.github_token_secret)
    secrets = None
    if wants_binding:
        key = transport.session_key()
        transport.probe_secret_source(args.github_token_secret, key)
        secrets = transport.github_binding(args.github_token_secret, key)
        prompt = bound_department_prompt(prompt)
    digest = ledger.prompt_digest(prompt)
    ledger_map = load_ledger(this_id)
    entry = ledger_map.get(request_id)
    if entry is not None:
        ledger.verify_request_payload(
            entry, department, ticket, profile_id, wd, digest, request_id
        )
        if ledger.reconcile_dispatch_entry(this_id, department, ticket, request_id, entry) == "reconciled":
            return
    else:
        ledger.refuse_duplicate_from_ledger(this_id, department, request_id, ledger_map, args.force)
        if args.force:
            ledger.refuse_duplicate_dispatch(this_id, {"department": department}, force=True)
    child_id = str((entry or {}).get("child_id") or "") or identity.dispatch_request_child_id(
        this_id, department, ticket, request_id
    )
    # Issue #53: inject the child's own id into the child runtime so its
    # sessions modes resolve identity explicitly (env first), and mirror it
    # into a tag when absent so the persisted child carries the binding.
    tags = identity.canvas_tags(parent)
    tags["department"] = department
    tags.setdefault("conversation_id", child_id)
    child_env = {
        **{str(k): str(v) for k, v in (parent.get("env") or {}).items() if isinstance(v, (str, int, float))},
        "OPENHANDS_CONVERSATION_ID": child_id,
    }
    # Carried correlated-session path (#24): a legacy --dispatch-id binds the
    # created child to the ticket so a follow-up GET can verify the identity
    # actually persisted before the dispatch is recorded as accepted.
    dispatch_id = ""
    if str(getattr(args, "dispatch_id", "") or "").strip():
        dispatch_id = identity.normalize_request_id(args.dispatch_id)
        tags["dispatch_id"] = dispatch_id
        tags["ticket"] = ticket
    body = conversation_body(
        child_id=child_id,
        profile_id=profile_id,
        working_dir=wd,
        prompt=prompt,
        tags=tags,
        max_iterations=args.max_iterations,
        parent_id=this_id,
        secrets=secrets,
        env=child_env,
    )
    payload, receipt, err = ledger.http_op(
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
        ledger.record_ledger(
            this_id,
            request_id,
            ledger.ledger_entry(
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
    if dispatch_id:
        # Fail-closed legacy verification: the created child must really
        # carry the correlation identity before it is recorded as accepted.
        validate_persisted_dispatch(
            transport.get_conversation(cid),
            cid,
            this_id,
            dispatch_id,
            department,
            ticket,
        )
    ledger.record_ledger(
        this_id,
        request_id,
        ledger.ledger_entry(
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
        "url": f"{transport.UI}/conversations/{cid}",
        "mode": "dispatch",
        "working_dir": wd,
        "this_id": this_id,
        "dispatch_id": dispatch_id,
        "child_conversation_id": cid,
        "github_binding": transport.binding_status(wants_binding),
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
        cur = transport.get_conversation(cid) or {}
        last = identity.status_of(cur)
        if last in identity.TERMINAL_STATES:
            print(json.dumps({"id": cid, "status": last}, ensure_ascii=False), flush=True)
            if last != "finished":
                sys.exit(2)
            return
    raise SystemExit(f"poll timeout status={last!r}")


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
