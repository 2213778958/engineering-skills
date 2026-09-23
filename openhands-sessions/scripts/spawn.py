#!/usr/bin/env python3
"""Create an Agent Canvas conversation in this imported workspace. Never print the API key."""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError  # re-exported for tests
from urllib.request import urlopen  # re-exported for test patch targets

sys.path.insert(0, str(Path(__file__).resolve().parent))

from canvas_sessions import dispatch, identity, ledger, notify, resume, transport
from canvas_sessions.identity import PROFILE_HINT
from canvas_sessions.transport import (
    BASE,
    KEY_PATH,
    UI,
    SECRET_NAME,
    GITHUB_CONSUMER,
    EVENT_POST_TIMEOUT,
    session_key,
    api,
    github_binding,
    probe_secret_source,
    binding_status,
    get_conversation,
    maybe_run,
    ensure_child,
)
from canvas_sessions.identity import (
    WT_SEGMENT,
    SIBLING_TREE,
    TICKET_FORM,
    REQUEST_FORM,
    TERMINAL_STATES,
    AUTHORIZED_DEPARTMENTS,
    DEPARTMENTS,
    working_dir_of,
    norm_path,
    refuse_path,
    canvas_tags,
    status_of,
    search_items,
    search_running,
    validate_profile_id,
    normalize_ticket,
    normalize_request_id,
    request_identity,
    dispatch_request_child_id,
    imported_from_cwd,
    cwd_match_paths,
    is_workspace_hit,
    updated_key,
    pick_workspace_id,
    resolve_this,
)
from canvas_sessions.ledger import (
    prompt_digest,
    ledger_dir,
    ledger_path,
    load_ledger,
    save_ledger,
    record_ledger,
    ledger_entry,
    make_receipt,
    emit_receipt,
    http_op,
    refuse_duplicate_dispatch,
    reconcile_event_marker,
    refuse_duplicate_from_ledger,
    verify_request_payload,
    reconciled_receipt,
    reconcile_dispatch_entry,
    resume_rejection,
    reconcile_resume_entry,
)
from canvas_sessions.dispatch import (
    bound_department_prompt,
    conversation_body,
    run_dispatch,
    validate_persisted_dispatch,
)
from canvas_sessions.resume import (
    post_message,
    validate_resume,
    run_resume,
)
from canvas_sessions.notify import (
    REPORT_PREFIX,
    REPORT_HOPS,
    report_fields,
    validate_report,
    event_payload,
    send_event,
    event_text_blob,
    target_event_texts,
    event_marker,
    run_notify,
)

PROFILE_ID_HELP = (
    "Agent Canvas profile UUID (GET /api/agent-profiles, key 'profiles'), "
    "not the profile name"
)

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

    this_id = identity.resolve_this(args.this_id.strip() or None)
    parent = transport.get_conversation(this_id)
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
        # F2 (issue #24): the main() resume path runs the same gate as the
        # run_resume API path — reject before any message/run POST when the
        # caller is not a parentless planning root or the direction is not
        # planning-root -> own direct department child.
        resume.run_resume(args, parent, this_id)
        return

    if args.mode == "notify":
        notify.run_notify(args, parent)
        return

    if args.mode == "dispatch":
        dispatch.run_dispatch(args, parent)
        return

    if not args.profile_id or not args.prompt_file:
        raise SystemExit("open needs --profile-id and --prompt-file")
    identity.validate_profile_id(args.profile_id)
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    wd = identity.working_dir_of(parent)
    if not wd:
        raise SystemExit("this conversation has no workspace.working_dir")
    why = identity.refuse_path(wd)
    if why:
        raise SystemExit(f"refuse this conversation working_dir {wd!r}: {why}")

    wants_binding = bool(args.department or args.github_token_secret)
    if bool(args.department) != bool(args.github_token_secret):
        raise SystemExit(
            "GitHub binding requires both --department and --github-token-secret"
        )
    secrets = None
    if wants_binding:
        key = transport.session_key()
        transport.probe_secret_source(args.github_token_secret, key)
        secrets = transport.github_binding(args.github_token_secret, key)
        prompt = dispatch.bound_department_prompt(prompt)

    tags = identity.canvas_tags(parent)
    child_id = str(uuid.uuid4())
    if args.department:
        tags["department"] = args.department
        if args.mode == "dispatch":
            ledger.refuse_duplicate_dispatch(this_id, tags, args.force)
            if not args.force:
                child_id = dispatch_child_id(this_id, args.department)
    if wants_binding:
        tags["githubbinding"] = "gh-token-bound"
    body = dispatch.conversation_body(
        child_id=child_id,
        profile_id=args.profile_id,
        working_dir=wd,
        prompt=prompt,
        tags=tags,
        max_iterations=args.max_iterations,
        parent_id=this_id if args.mode == "dispatch" else None,
        secrets=secrets,
    )

    created = transport.api(
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
    checked = dispatch.ensure_child(cid, tags)
    got = identity.working_dir_of(checked)
    if got != wd:
        raise SystemExit(f"working_dir mismatch: got {got!r} want {wd!r}")
    report = {
        "id": checked.get("id") or cid,
        "conversation_id": checked.get("conversation_id") or checked.get("id") or cid,
        "url": f"{transport.UI}/conversations/{cid}",
        "mode": args.mode,
        "department": args.department,
        "ticket": args.ticket or None,
        "working_dir": got,
        "tags": checked.get("tags") if isinstance(checked.get("tags"), dict) else {},
        "parent_conversation_id": checked.get("parent_conversation_id"),
        "max_iterations": args.max_iterations,
        "launched_agent_profile": checked.get("launched_agent_profile"),
        "this_id": this_id,
        "github_binding": transport.binding_status(wants_binding),
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
        cur = transport.get_conversation(cid, timeout=180) or {}
        last = identity.status_of(cur)
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
