#!/usr/bin/env python3
"""Native owner/clear checks. Run only in an isolated Xvfb display."""

import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import time

if os.getuid() == 0:
    raise SystemExit("Run X11 tests as the normal desktop user, without sudo.")
if os.environ.get("JARVIS_ISOLATED_X11_TEST") != "1":
    raise SystemExit("Use JARVIS_ISOLATED_X11_TEST=1 xvfb-run --auto-servernum python3 " + __file__)

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "system_helpers/jarvis-reading-clipboard"
X11 = runpy.run_path(str(GUARD), run_name="native_clipboard_test")["X11"]


def wait_for(check, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.02)
    raise AssertionError("Native clipboard check timed out")


def copy(text):
    child = subprocess.Popen(["xclip", "-selection", "clipboard", "-quiet", "-i"],
                             stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    child.stdin.write(text)
    child.stdin.close()
    return child


with tempfile.TemporaryDirectory(prefix="jarvis-x11-clipboard-") as directory:
    folder = Path(directory)
    for case in ("accept", "same-copy", "expiry"):
        ready = folder / "ready"
        ready.write_text("")
        guard = subprocess.Popen(
            ["bash", "-c", 'exec python3 "$1" 8>"$2"', "clipboard-test", str(GUARD), str(ready)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        guard.stdin.write(b"Harmless clipboard test")
        guard.stdin.close()
        connection, replacement = X11(), None
        try:
            wait_for(lambda: ready.stat().st_size > 0, 3)
            owner = connection.owner()
            assert owner and connection.pid(owner) > 0
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                    capture_output=True, timeout=2, check=True)
            assert result.stdout == b"Harmless clipboard test"
            if case == "same-copy":
                replacement = copy(b"Harmless clipboard test")
                wait_for(lambda: connection.pid(connection.owner()) == replacement.pid, 2)
                guard.wait(timeout=3)
                assert connection.pid(connection.owner()) == replacement.pid
            elif case == "accept":
                guard.terminate()
                assert guard.wait(timeout=3) == 0
                assert connection.owner() == 0
            else:
                # No parent request for cleanup: the independent deadline wins.
                assert guard.wait(timeout=18) == 0
                assert connection.owner() == 0
            print("PASS: native X11", case)
        finally:
            if guard.poll() is None:
                guard.terminate()
                guard.wait(timeout=3)
            if replacement is not None:
                replacement.terminate()
                replacement.wait(timeout=3)
            connection.close()
print("PASS: native process identity, explicit clear, same-text copy and expiry")
