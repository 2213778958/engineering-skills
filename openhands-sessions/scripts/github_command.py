#!/usr/bin/env python3
"""Run a GitHub CLI command with one explicitly configured registered secret."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence


def redact(text: str, secret: str) -> str:
    """Remove the credential value from diagnostic text.

    Args:
        text: Text that may contain the credential.
        secret: Credential value to remove.

    Returns:
        Text safe to print.
    """
    return text.replace(secret, "[REDACTED]") if secret else text


def run_github_command(key_name: str, secret: str, command: Sequence[str]) -> int:
    """Authenticate and run a gh command with command-scoped GH_TOKEN.

    Args:
        key_name: Registered secret name configured by the process latch.
        secret: Value supplied through stdin by an explicit shell reference.
        command: GitHub CLI argument vector, beginning with ``gh``.

    Returns:
        The command exit code.
    """
    if key_name == "none":
        raise SystemExit("credential none: github-dependent operations unavailable")
    if not key_name or "=" in key_name:
        raise SystemExit(f"credential invalid-key-name: {key_name or '<empty>'}")
    secret = secret.strip()
    if not secret:
        raise SystemExit(f"credential unavailable: {key_name}")
    if not command or os.path.basename(command[0]).lower() not in {"gh", "gh.exe", "gh.cmd"}:
        raise SystemExit("credential invalid-consumer: command must begin with gh")

    env = os.environ.copy()
    env["GH_TOKEN"] = secret
    check = subprocess.run(
        [command[0], "auth", "status"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode:
        detail = redact((check.stderr or check.stdout).strip(), secret)
        suffix = f": {detail}" if detail else ""
        raise SystemExit(f"credential authentication-failed: {key_name}{suffix}")

    result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    if result.stdout:
        print(redact(result.stdout, secret), end="")
    if result.stderr:
        print(redact(result.stderr, secret), end="", file=sys.stderr)
    return result.returncode


def main() -> None:
    """Parse the configured key and execute one authenticated gh command."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-name", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    secret = "" if args.key_name == "none" else sys.stdin.readline()
    raise SystemExit(run_github_command(args.key_name, secret, command))


if __name__ == "__main__":
    main()
