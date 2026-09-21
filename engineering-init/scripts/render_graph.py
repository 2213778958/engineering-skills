#!/usr/bin/env python3
"""Render a Mermaid DAG from GitHub issue dependencies (shared)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


MARKER_OPEN = "<!-- engineering:graph -->"
MARKER_CLOSE = "<!-- /engineering:graph -->"
LEGACY_OPEN = "<!-- github-engineering:graph -->"
LEGACY_CLOSE = "<!-- /github-engineering:graph -->"
ISSUE_RE = re.compile(
    r"(?:https://github\.com/[^/\s]+/[^/\s]+/issues/|#)(\d+)\b",
    re.IGNORECASE,
)
HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}(?![0-9A-Fa-f])")
PART_OF_RE = re.compile(r"Part of\s+#(\d+)", re.IGNORECASE)
TASK_ITEM_RE = re.compile(
    r"^\s*[-*]\s+\[[ xX]\]\s+.*?(?:#|issues/)(\d+)",
    re.MULTILINE,
)


def strip_graph_blocks(body: str) -> str:
    text = body or ""
    for open_, close in (
        (MARKER_OPEN, MARKER_CLOSE),
        (LEGACY_OPEN, LEGACY_CLOSE),
    ):
        text = re.sub(
            re.escape(open_) + r".*?" + re.escape(close),
            "",
            text,
            flags=re.DOTALL,
        )
    return text


def issue_scan_text(body: str) -> str:
    return HEX_COLOR_RE.sub("", strip_graph_blocks(body or ""))


def run_gh(args: list[str], stage: str) -> str:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "gh failed"
        raise QueryError(stage, detail)
    return proc.stdout


def gh_json(args: list[str], stage: str) -> Any:
    try:
        return json.loads(run_gh(args, stage))
    except json.JSONDecodeError as exc:
        raise QueryError(stage, f"invalid JSON: {exc}") from exc


def repo_name() -> str:
    data = gh_json(["repo", "view", "--json", "nameWithOwner"], "repository identity")
    try:
        return str(data["nameWithOwner"])
    except (KeyError, TypeError) as exc:
        raise QueryError("repository identity", "response lacks nameWithOwner") from exc


def view_issue(number: int, owner_repo: str) -> dict[str, Any]:
    fields = "number,title,state,url,body,blockedBy,blocking"
    return gh_json(
        ["issue", "view", str(number), "--repo", owner_repo, "--json", fields],
        f"issue view #{number} in {owner_repo}",
    )


def issue_numbers(items: Any) -> list[int]:
    out: list[int] = []
    if not items:
        return out
    for item in items:
        if isinstance(item, dict) and item.get("number") is not None:
            out.append(int(item["number"]))
        elif isinstance(item, int):
            out.append(item)
    return out


def rest_dep_numbers(owner_repo: str, number: int, kind: str) -> list[int]:
    raw = run_gh(
        [
            "api",
            f"repos/{owner_repo}/issues/{number}/dependencies/{kind}",
            "--paginate",
        ],
        f"{kind} dependencies for #{number} in {owner_repo}",
    )
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QueryError(
            f"{kind} dependencies for #{number} in {owner_repo}",
            f"invalid JSON: {exc}",
        ) from exc
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if not isinstance(data, list):
        return []
    nums: list[int] = []
    for item in data:
        if isinstance(item, dict):
            n = item.get("number") or (item.get("issue") or {}).get("number")
            if n is not None:
                nums.append(int(n))
    return nums


def sub_issue_numbers(owner_repo: str, number: int) -> list[int]:
    raw = run_gh(
        ["api", f"repos/{owner_repo}/issues/{number}/sub_issues", "--paginate"],
        f"sub-issues for #{number} in {owner_repo}",
    )
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QueryError(
            f"sub-issues for #{number} in {owner_repo}", f"invalid JSON: {exc}"
        ) from exc
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if not isinstance(data, list):
        return []
    return [int(item["number"]) for item in data if isinstance(item, dict) and "number" in item]


def part_of_children(spec: int, owner_repo: str) -> list[int]:
    rows = gh_json(
        [
            "issue",
            "list",
            "--repo",
            owner_repo,
            "--state",
            "all",
            "--limit",
            "100",
            "--search",
            f'"Part of #{spec}"',
            "--json",
            "number,body",
        ],
        f"Part-of search for #{spec} in {owner_repo}",
    )
    out: list[int] = []
    for row in rows:
        n = int(row["number"])
        body = row.get("body") or ""
        if n != spec and (
            f"Part of #{spec}" in body or PART_OF_RE.search(body)
        ):
            if any(int(m.group(1)) == spec for m in PART_OF_RE.finditer(body)):
                out.append(n)
    return out


def body_refs(body: str, spec: int | None = None) -> list[int]:
    text = issue_scan_text(body)
    nums = [int(m.group(1)) for m in TASK_ITEM_RE.finditer(text)]
    for m in ISSUE_RE.finditer(text):
        nums.append(int(m.group(1)))
    return [n for n in nums if spec is None or n != spec]


def merge_deps(meta: dict[str, Any], owner_repo: str, number: int) -> tuple[list[int], list[int]]:
    blocked_by = issue_numbers(meta.get("blockedBy"))
    blocking = issue_numbers(meta.get("blocking"))
    if not blocked_by:
        blocked_by = rest_dep_numbers(owner_repo, number, "blocked_by")
    if not blocking:
        blocking = rest_dep_numbers(owner_repo, number, "blocking")
    body = meta.get("body") or ""
    if not blocked_by:
        m = re.search(r"Blocked by:\s*(.+)", body, re.IGNORECASE)
        if m:
            blocked_by = [int(x) for x in ISSUE_RE.findall(m.group(1))]
    return sorted(set(blocked_by)), sorted(set(blocking))


def collect(spec: int, owner_repo: str) -> dict[int, dict[str, Any]]:
    seeds = {spec}
    seeds.update(sub_issue_numbers(owner_repo, spec))
    seeds.update(part_of_children(spec, owner_repo))
    spec_meta = view_issue(spec, owner_repo)
    seeds.update(body_refs(spec_meta.get("body") or "", spec=spec))

    nodes: dict[int, dict[str, Any]] = {}
    pending = set(seeds)
    while pending:
        n = pending.pop()
        if n in nodes:
            continue
        meta = spec_meta if n == spec else view_issue(n, owner_repo)
        blocked_by, blocking = merge_deps(meta, owner_repo, n)
        meta["_blocked_by"] = blocked_by
        meta["_blocking"] = blocking
        nodes[n] = meta
        for other in blocked_by + blocking:
            if other not in nodes:
                pending.add(other)

    if spec in nodes:
        only_container = not nodes[spec]["_blocked_by"] and not nodes[spec]["_blocking"]
        children = seeds - {spec}
        if only_container and children:
            del nodes[spec]
    return nodes


class QueryError(RuntimeError):
    """A required GitHub query failed, including its original stderr."""

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(f"{stage}: {detail}")
        self.stage = stage
        self.detail = detail


GRAPH_TITLE = "Graph（流程）"


def mermaid(nodes: dict[int, dict[str, Any]]) -> str:
    lines = [
        "flowchart TD",
        "classDef open fill:#347d39,color:#FFFFFF,stroke-width:0px;",
        "classDef closed fill:#8256d0,color:#FFFFFF,stroke-width:0px;",
        "",
    ]
    for n in sorted(nodes):
        title = re.sub(r'["\[\]]', "", str(nodes[n].get("title") or ""))
        klass = "closed" if str(nodes[n].get("state", "")).lower() == "closed" else "open"
        lines.append(f'i{n}["#{n} {title}"]:::{klass}')
    lines.append("")
    for n, meta in sorted(nodes.items()):
        for blocker in meta["_blocked_by"]:
            if blocker in nodes:
                lines.append(f"i{blocker} --> i{n}")
    lines.append("")
    for n, meta in sorted(nodes.items()):
        url = meta.get("url") or ""
        if url:
            lines.append(f'click i{n} href "{url}" _blank')
    return "\n".join(lines) + "\n"


def degrees(nodes: dict[int, dict[str, Any]]) -> tuple[list[int], list[int]]:
    incoming: dict[int, int] = {n: 0 for n in nodes}
    outgoing: dict[int, int] = {n: 0 for n in nodes}
    for n, meta in nodes.items():
        for blocker in meta["_blocked_by"]:
            if blocker in nodes:
                incoming[n] += 1
                outgoing[blocker] += 1
    sources = [n for n in sorted(nodes) if incoming[n] == 0]
    sinks = [n for n in sorted(nodes) if outgoing[n] == 0]
    return sources, sinks


def upsert_body(body: str, diagram: str) -> str:
    block = (
        f"{MARKER_OPEN}\n\n"
        f"### {GRAPH_TITLE}\n\n"
        f"```mermaid\n{diagram.strip()}\n```\n\n"
        f"{MARKER_CLOSE}"
    )
    text = body or ""
    if LEGACY_OPEN in text and LEGACY_CLOSE in text:
        text = re.sub(
            re.escape(LEGACY_OPEN) + r".*?" + re.escape(LEGACY_CLOSE),
            block,
            text,
            count=1,
            flags=re.DOTALL,
        )
        return text
    if MARKER_OPEN in text and MARKER_CLOSE in text:
        return re.sub(
            re.escape(MARKER_OPEN) + r".*?" + re.escape(MARKER_CLOSE),
            block,
            text,
            count=1,
            flags=re.DOTALL,
        )
    return text.rstrip() + "\n\n## " + GRAPH_TITLE + "\n\n" + block + "\n"


def write_spec(number: int, owner_repo: str, diagram: str) -> None:
    current = view_issue(number, owner_repo)
    new_body = upsert_body(current.get("body") or "", diagram)
    path = _write_temp(new_body)
    try:
        run_gh(
            [
                "issue",
                "edit",
                str(number),
                "--repo",
                owner_repo,
                "--body-file",
                str(path),
            ],
            f"write graph to #{number} in {owner_repo}",
        )
    finally:
        path.unlink(missing_ok=True)


def _write_temp(text: str) -> Path:
    tmp = NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".md", delete=False, newline="\n"
    )
    tmp.write(text)
    tmp.close()
    return Path(tmp.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render issue dependency mermaid")
    parser.add_argument("--issue", type=int, required=True, help="spec issue number")
    parser.add_argument("--write", action="store_true", help="upsert mermaid on the spec")
    parser.add_argument("--force", action="store_true", help="write even with --strict-one-one")
    parser.add_argument(
        "--strict-one-one",
        action="store_true",
        help="exit 2 unless exactly one source and one sink",
    )
    args = parser.parse_args()

    try:
        owner_repo = repo_name()
        nodes = collect(args.issue, owner_repo)
    except QueryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    diagram = mermaid(nodes)
    sources, sinks = degrees(nodes)
    print(diagram)
    print(
        f"sources={sources} sinks={sinks} nodes={sorted(nodes)} repo={owner_repo}",
        file=sys.stderr,
    )
    one_one = len(sources) == 1 and len(sinks) == 1
    if not one_one:
        print("not a one-source one-sink DAG (default, not required)", file=sys.stderr)
        if args.strict_one_one and not args.force:
            return 2

    if args.write:
        try:
            write_spec(args.issue, owner_repo, diagram)
        except QueryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote graph to {owner_repo}#{args.issue}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
