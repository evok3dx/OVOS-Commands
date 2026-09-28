#!/usr/bin/env python3
"""Relaunch the installed Jarvis GUI after the old process has exited."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import time


def wait_for_exit(pid: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        except PermissionError as error:
            raise RuntimeError("Cannot verify the previous GUI process") from error
        time.sleep(0.1)
    raise RuntimeError("Previous Control Centre did not exit in time")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-pid", type=int, required=True)
    parser.add_argument("--launcher", type=Path, required=True)
    args = parser.parse_args()
    if args.wait_pid <= 1:
        raise ValueError("Invalid GUI process identifier")
    expected = Path.home()/'.local/bin/jarvis-setup'
    launcher = args.launcher.expanduser()
    if launcher != expected or not launcher.is_file() or launcher.is_symlink():
        raise RuntimeError("Refusing an unexpected Control Centre launcher")
    wait_for_exit(args.wait_pid)
    subprocess.Popen(
        [str(launcher), '--gui', '--tab', 'updates'],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
