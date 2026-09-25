#!/usr/bin/env python3
"""Acceptance reachability and scope guard (git only).

``pre``: before opening the PR. Every ticket in scope resolves to exactly one
``<remote>/feat/<n>-*`` or ``<remote>/fix/<n>-*`` branch and is an ancestor of
the merge head. Every non-merge commit the head adds over the default branch
belongs to a ticket in scope: its owner is the lowest ticket branch that
contains it, so a scope branch stacked on an out-of-scope branch still fails.
A clean merge commit must equal the re-merge of its parents; a merge that
resolved conflicts is listed as REVIEW for the acceptance review. Needs git 2.38+
(``merge-tree --write-tree``). Owner ties go to the lower ticket number; a stale
remote ticket branch cut from an earlier commit of a scope branch can claim
those commits, so delete abandoned ticket branches. A ticket whose branch is
gone cannot own commits in ``pre``.

``post``: after the PR merged, before closing the acceptance. Every ticket
branch is an ancestor of ``<remote>/<default>``. ``--tickets <n>=<sha>`` checks
the SHA printed by ``pre`` when the branch was deleted after merge.

Prints one line per check and exits non-zero when any check fails.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def out(repo: Path, *args: str) -> str:
    return git(repo, *args).stdout.strip()


def default_branch(repo: Path, remote: str, given: str | None) -> str:
    if given:
        return given
    head = out(repo, "symbolic-ref", "--quiet", "--short", f"refs/remotes/{remote}/HEAD")
    return head.split("/", 1)[1] if head.startswith(f"{remote}/") else "main"


def ticket_branches(repo: Path, remote: str) -> dict[str, int]:
    pattern = re.compile(rf"^{re.escape(remote)}/(?:feat|fix)/(\d+)-[^/]+$")
    refs = out(repo, "for-each-ref", "--format=%(refname:short)",
               f"refs/remotes/{remote}/feat", f"refs/remotes/{remote}/fix").split()
    return {ref: int(m.group(1)) for ref in refs if (m := pattern.match(ref))}


def parse_ticket(value: str) -> tuple[int, str | None]:
    number, _, sha = value.partition("=")
    if not number.isdigit():
        raise argparse.ArgumentTypeError(f"ticket must be <n> or <n>=<sha>: {value}")
    return int(number), sha or None


def rev_set(repo: Path, *args: str) -> set[str]:
    return set(out(repo, "rev-list", *args).split())


def is_ancestor(repo: Path, ref: str, target: str) -> bool:
    return git(repo, "merge-base", "--is-ancestor", ref, target).returncode == 0


def subject(repo: Path, sha: str) -> str:
    return out(repo, "log", "-1", "--format=%h %s", sha)


class Checker:
    def __init__(self, repo: Path, remote: str, default: str) -> None:
        self.repo = repo
        self.remote = remote
        self.base = f"{remote}/{default}"
        self.branches = ticket_branches(repo, remote)
        self.failures = 0

    def fail(self, line: str) -> None:
        print(f"FAIL {line}")
        self.failures += 1

    def resolve(self, ticket: int, sha: str | None) -> str | None:
        refs = sorted(ref for ref, n in self.branches.items() if n == ticket)
        if len(refs) == 1:
            return refs[0]
        if len(refs) > 1:
            self.fail(f"#{ticket}: several branches: {', '.join(refs)}")
            return None
        if sha:
            print(f"note #{ticket}: branch gone; checking {sha}")
            return sha
        self.fail(f"#{ticket}: no {self.remote}/feat/{ticket}-* or {self.remote}/fix/{ticket}-* branch")
        return None

    def reachable(self, tickets: list[tuple[int, str | None]], target: str) -> None:
        for ticket, sha in tickets:
            ref = self.resolve(ticket, sha)
            if ref is None:
                continue
            tip = out(self.repo, "rev-parse", "--short", ref)
            if is_ancestor(self.repo, ref, target):
                print(f"ok   #{ticket}: {ref} ({tip}) is an ancestor of {target}")
            else:
                self.fail(f"#{ticket}: {ref} ({tip}) is not an ancestor of {target}")

    def head_matches_remote(self, head: str) -> None:
        if head.startswith(f"{self.remote}/"):
            return
        remote_head = f"{self.remote}/{head}"
        if git(self.repo, "rev-parse", "--verify", "--quiet", remote_head).returncode != 0:
            return
        if out(self.repo, "rev-parse", head) != out(self.repo, "rev-parse", remote_head):
            print(f"note head: {remote_head} is stale; manage force-pushes {head} after pre passes")

    def scope(self, head: str, scope: set[int]) -> None:
        added = rev_set(self.repo, "--no-merges", f"{self.base}..{head}")
        owned = {ref: rev_set(self.repo, f"{self.base}..{ref}") for ref in self.branches}
        bad = 0
        for sha in sorted(added):
            owners = sorted((len(revs), self.branches[ref]) for ref, revs in owned.items() if sha in revs)
            if not owners:
                self.fail(f"scope: {subject(self.repo, sha)} is not on any ticket branch")
                bad += 1
            elif owners[0][1] not in scope:
                self.fail(f"scope: {subject(self.repo, sha)} belongs to #{owners[0][1]}, outside --tickets")
                bad += 1
        if not bad:
            print(f"ok   scope: {len(added)} commit(s) over {self.base}, all owned by tickets in scope")

    def merges(self, head: str) -> None:
        for sha in out(self.repo, "rev-list", "--merges", f"{self.base}..{head}").split():
            parents = out(self.repo, "rev-list", "--parents", "-n", "1", sha).split()[1:]
            if len(parents) != 2:
                print(f"REVIEW merge {subject(self.repo, sha)}: {len(parents)} parents; review `git show --cc {sha[:12]}`")
                continue
            remerge = git(self.repo, "merge-tree", "--write-tree", *parents)
            if remerge.returncode > 1:
                self.fail("merge-tree unavailable (git 2.38+ required)")
                return
            if remerge.returncode == 1:
                print(f"REVIEW merge {subject(self.repo, sha)}: resolved conflicts; review `git show --cc {sha[:12]}`")
            elif remerge.stdout.split()[0] == out(self.repo, "rev-parse", f"{sha}^{{tree}}"):
                print(f"ok   merge {subject(self.repo, sha)}: equals the re-merge of its parents")
            else:
                self.fail(f"merge {subject(self.repo, sha)}: content differs from the clean re-merge of its parents")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("pre", "post"))
    parser.add_argument("--tickets", type=parse_ticket, nargs="+", required=True,
                        help="implement tickets in scope: <n> or <n>=<sha>")
    parser.add_argument("--head", help="merge head (pre only): the single head branch or merge/<n>")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--default", help="default branch (default: <remote>/HEAD, else main)")
    args = parser.parse_args(argv)
    if args.mode == "pre" and not args.head:
        parser.error("pre needs --head")
    default = default_branch(args.repo, args.remote, args.default)
    checker = Checker(args.repo, args.remote, default)
    if git(args.repo, "rev-parse", "--verify", "--quiet", checker.base).returncode != 0:
        print(f"FAIL {checker.base} not found (fetch, or pass --default)")
        return 1
    if args.mode == "pre":
        if git(args.repo, "rev-parse", "--verify", "--quiet", args.head).returncode != 0:
            print(f"FAIL head {args.head} not found")
            return 1
        print(f"head {args.head} = {out(args.repo, 'rev-parse', args.head)}")
        checker.head_matches_remote(args.head)
        checker.reachable(args.tickets, args.head)
        checker.scope(args.head, {ticket for ticket, _ in args.tickets})
        checker.merges(args.head)
    else:
        checker.reachable(args.tickets, checker.base)
    result = "pass" if checker.failures == 0 else f"fail ({checker.failures})"
    print(f"{args.mode}: {result}")
    return 0 if checker.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
