#!/usr/bin/env python3
"""Acceptance reachability and scope guard (git only).

``pre``: before opening the PR. Every implement ticket in scope resolves to
exactly one ``<remote>/feat/<n>-*`` or ``<remote>/fix/<n>-*`` branch, each
branch is an ancestor of the merge head, and every non-merge commit the head
adds over the default branch comes from one of those branches.

``post``: after the PR merged, before closing the acceptance. Every branch is
an ancestor of ``<remote>/<default>``.

Prints one line per check and exits non-zero when any check fails.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def resolve(repo: Path, remote: str, ticket: int) -> tuple[str | None, str]:
    """Return the ticket branch ref, or ``None`` and the reason."""
    out = git(repo, "for-each-ref", "--format=%(refname:short)",
              f"refs/remotes/{remote}/feat/{ticket}-*", f"refs/remotes/{remote}/fix/{ticket}-*")
    refs = out.stdout.split()
    if len(refs) == 1:
        return refs[0], "ok"
    if not refs:
        return None, f"no {remote}/feat/{ticket}-* or {remote}/fix/{ticket}-* branch"
    return None, "several branches: " + ", ".join(refs)


def is_ancestor(repo: Path, ref: str, head: str) -> bool:
    return git(repo, "merge-base", "--is-ancestor", ref, head).returncode == 0


def rev_list(repo: Path, *args: str) -> set[str]:
    return set(git(repo, "rev-list", *args).stdout.split())


def check(repo: Path, mode: str, remote: str, default: str, head: str | None, tickets: list[int]) -> int:
    base = f"{remote}/{default}"
    target = head if mode == "pre" else base
    failures = 0
    branches: list[str] = []
    for ticket in tickets:
        ref, reason = resolve(repo, remote, ticket)
        if ref is None:
            print(f"FAIL #{ticket}: {reason}")
            failures += 1
            continue
        branches.append(ref)
        if is_ancestor(repo, ref, target):
            print(f"ok   #{ticket}: {ref} is an ancestor of {target}")
        else:
            print(f"FAIL #{ticket}: {ref} is not an ancestor of {target}")
            failures += 1
    if mode == "pre" and head is not None:
        added = rev_list(repo, "--no-merges", f"{base}..{head}")
        covered: set[str] = set()
        for ref in branches:
            covered |= rev_list(repo, f"{base}..{ref}")
        stray = sorted(added - covered)
        for sha in stray:
            subject = git(repo, "log", "-1", "--format=%h %s", sha).stdout.strip()
            print(f"FAIL scope: {subject} is not on any ticket branch")
        failures += len(stray)
        if not stray:
            print(f"ok   scope: {len(added)} commit(s) over {base}, all from ticket branches")
    print(f"{mode}: {'pass' if failures == 0 else f'fail ({failures})'}")
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("pre", "post"))
    parser.add_argument("--tickets", type=int, nargs="+", required=True,
                        help="implement tickets in this acceptance's blocked-by scope")
    parser.add_argument("--head", help="merge head (pre only): the head branch or merge/<n>")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--default", default="main", help="default branch name")
    args = parser.parse_args(argv)
    if args.mode == "pre" and not args.head:
        parser.error("pre needs --head")
    if git(args.repo, "rev-parse", "--verify", "--quiet", f"{args.remote}/{args.default}").returncode != 0:
        print(f"FAIL: {args.remote}/{args.default} not found; run git fetch")
        return 1
    return check(args.repo, args.mode, args.remote, args.default, args.head, args.tickets)


if __name__ == "__main__":
    sys.exit(main())
