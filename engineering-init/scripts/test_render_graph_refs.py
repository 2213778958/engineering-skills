#!/usr/bin/env python3
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

import render_graph
from render_graph import ISSUE_RE, body_refs, issue_scan_text, mermaid

RENDERER = Path(__file__).with_name("render_graph.py")

MERMAID = """
<!-- engineering:graph -->
```mermaid
classDef closed fill:#8256d0,color:#FFFFFF,stroke-width:0px;
i15["#15 三关通关可玩包"]:::open
i8256["#8256 ghost"]:::closed
```
<!-- /engineering:graph -->
"""


def run_renderer(mode: str, *args: str) -> tuple[subprocess.CompletedProcess[str], str]:
    edits: list[str] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        gh_args = command[1:]
        if gh_args[:2] == ["repo", "view"]:
            return subprocess.CompletedProcess(command, 0, '{"nameWithOwner":"acme/widgets"}\n', "")
        if gh_args[:2] == ["issue", "list"]:
            if mode == "issue-list-failure":
                return subprocess.CompletedProcess(command, 17, "", "fake stderr: issue-list")
            return subprocess.CompletedProcess(command, 0, "[]\n", "")
        if gh_args[:2] == ["issue", "view"]:
            if mode == "issue-view-failure":
                return subprocess.CompletedProcess(command, 17, "", "fake stderr: issue-view")
            number = int(gh_args[2])
            blocked = [{"number": 8}] if mode == "graph" and number == 7 else []
            body = "existing graph" if mode in {"issue-list-failure", "issue-view-failure", "dependency-failure", "sub-issue-failure"} else ""
            state = "closed" if mode == "sub-issue-graph" and number == 46 else "open"
            payload = {"number": number, "title": f"issue-{number}", "state": state, "url": f"https://github.com/acme/widgets/issues/{number}", "body": body, "blockedBy": blocked, "blocking": []}
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if gh_args[:2] == ["issue", "edit"]:
            edits.append("edit")
            return subprocess.CompletedProcess(command, 0, "", "")
        if gh_args[:1] == ["api"]:
            endpoint = gh_args[1]
            if endpoint.endswith("/sub_issues"):
                if mode == "sub-issue-failure":
                    return subprocess.CompletedProcess(command, 17, "", "fake stderr: sub-issues")
                if mode == "graph":
                    data = [{"number": 8}]
                elif mode == "sub-issue-graph" and endpoint.endswith("/issues/41/sub_issues"):
                    data = [{"number": 46}]
                else:
                    data = []
                return subprocess.CompletedProcess(command, 0, json.dumps(data), "")
            if "/dependencies/" in endpoint:
                if mode in {"blocked-by-failure", "blocking-failure"} and endpoint.endswith("/" + ("blocked_by" if mode == "blocked-by-failure" else "blocking")):
                    return subprocess.CompletedProcess(command, 17, "", "fake stderr: dependencies")
                return subprocess.CompletedProcess(command, 0, "[]", "")
        raise AssertionError(command)

    output = io.StringIO()
    errors = io.StringIO()
    original = render_graph.subprocess.run
    render_graph.subprocess.run = fake_run
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = render_graph.main.__wrapped__() if hasattr(render_graph.main, "__wrapped__") else None
            if code is None:
                parser_args = list(args)
                old_argv = sys.argv
                sys.argv = [str(RENDERER), *parser_args]
                try:
                    code = render_graph.main()
                finally:
                    sys.argv = old_argv
    finally:
        render_graph.subprocess.run = original
    return subprocess.CompletedProcess(args, code, output.getvalue(), errors.getvalue()), "\n".join(edits)


def assert_query_failure(mode: str, stage: str) -> None:
    result, edits = run_renderer(mode, "--issue", "7", "--write")
    assert result.returncode != 0, (result.returncode, result.stdout, result.stderr)
    assert stage in result.stderr
    assert "fake stderr" in result.stderr
    assert edits == ""


def main() -> int:
    prose = "Part of #2. See #15."
    assert ISSUE_RE.findall(issue_scan_text("fill:#8256d0,color:#FFFFFF")) == []
    assert 8256 not in body_refs(MERMAID + prose, spec=2)
    assert body_refs(MERMAID + prose, spec=2) == [15]
    assert body_refs("Blocked by: #8 #9\n" + MERMAID, spec=2) == [8, 9]
    drawn = mermaid(
        {15: {"title": "x", "state": "open", "url": "", "_blocked_by": []}}
    )
    assert drawn.startswith("flowchart TD")
    assert not drawn.startswith("---")

    sub_graph, _ = run_renderer("sub-issue-graph", "--issue", "41")
    assert sub_graph.returncode == 0, sub_graph.stderr
    assert 'i46["#46 issue-46"]:::closed' in sub_graph.stdout
    assert "i41 -.-> i46" in sub_graph.stdout
    assert 'click i46 href "https://github.com/acme/widgets/issues/46" _blank' in sub_graph.stdout

    assert_query_failure("issue-list-failure", "Part-of search")
    assert_query_failure("issue-view-failure", "issue view")
    assert_query_failure("blocked-by-failure", "blocked_by dependencies")
    assert_query_failure("blocking-failure", "blocking dependencies")
    assert_query_failure("sub-issue-failure", "sub-issues")

    empty, _ = run_renderer("empty", "--issue", "7")
    assert empty.returncode == 0, empty.stderr
    assert "nodes=[7]" in empty.stderr
    assert "i7[" in empty.stdout

    graph, _ = run_renderer("graph", "--issue", "7")
    assert graph.returncode == 0, graph.stderr
    assert 'i8["#8 issue-8"]' in graph.stdout
    assert 'i8 --> i7' in graph.stdout
    assert "repo=acme/widgets" in graph.stderr

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
