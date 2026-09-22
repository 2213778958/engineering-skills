#!/usr/bin/env python3
"""Run the repository verification stages with bounded execution."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGES = (
    ("render_graph_refs", (sys.executable, "engineering-init/scripts/test_render_graph_refs.py")),
    ("watch", (sys.executable, "openhands-watch/scripts/test_watch.py")),
)
TIMEOUT_EXIT_CODE = 124


def _popen_kwargs() -> dict[str, object]:
    """Return platform-specific options that isolate a stage process tree."""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _terminate_tree(process: subprocess.Popen[str]) -> None:
    """Terminate only the supplied process and its descendants."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)


def _write_output(stream: object, text: str) -> None:
    """Forward captured stage output without changing its contents."""
    if not text:
        return
    target = stream
    assert hasattr(target, "write")
    target.write(text)  # type: ignore[union-attr]
    target.flush()  # type: ignore[union-attr]


def run_stage(name: str, command: tuple[str, ...], timeout: float) -> int:
    """Run one stage, forwarding output and returning its process status.

    Args:
        name: Human-readable stage name.
        command: Executable and arguments for the stage.
        timeout: Maximum number of seconds allowed for the stage.

    Returns:
        The child return code, or 124 when the stage timed out.
    """
    started = time.monotonic()
    print(f"[{name}] start timeout={timeout:g}s", flush=True)
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **_popen_kwargs(),
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        timed_out = True
        _terminate_tree(process)
        stdout, stderr = process.communicate()
        if not stdout:
            stdout = error.output or ""
        if not stderr:
            stderr = error.stderr or ""
    _write_output(sys.stdout, stdout)
    _write_output(sys.stderr, stderr)
    elapsed = time.monotonic() - started
    if timed_out:
        print(f"[{name}] timeout after {elapsed:.2f}s returncode={TIMEOUT_EXIT_CODE}", flush=True)
        return TIMEOUT_EXIT_CODE
    returncode = process.returncode
    print(f"[{name}] finished in {elapsed:.2f}s returncode={returncode}", flush=True)
    return returncode


def run_verification(render_timeout: float, watch_timeout: float) -> int:
    """Run both verification stages serially and stop at the first failure."""
    for (name, command), timeout in zip(STAGES, (render_timeout, watch_timeout)):
        returncode = run_stage(name, command, timeout)
        if returncode != 0:
            return returncode
    return 0


def _positive_timeout(value: str) -> float:
    timeout = float(value)
    if timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than zero")
    return timeout


def main() -> int:
    """Parse timeout options and run the verification stages."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=_positive_timeout, default=60.0,
                        help="default timeout for each stage (seconds)")
    parser.add_argument("--render-timeout", type=_positive_timeout,
                        help="render_graph_refs stage timeout (seconds)")
    parser.add_argument("--watch-timeout", type=_positive_timeout,
                        help="watch stage timeout (seconds)")
    args = parser.parse_args()
    return run_verification(
        args.render_timeout if args.render_timeout is not None else args.timeout,
        args.watch_timeout if args.watch_timeout is not None else args.timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
