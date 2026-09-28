#!/usr/bin/env python3
"""Verify that Control Centre cancellation targets only its updater group."""

import importlib.util
from pathlib import Path
import sys
import threading
import time


source = Path(__file__).resolve().with_name("control_runtime.py")
spec = importlib.util.spec_from_file_location("control_update_cancel", source)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

completed = runtime._run_cancellable_update(
    [sys.executable, "-c", "print('complete')"], threading.Event(), timeout=5)
assert completed.returncode == 0
assert completed.stdout.strip() == "complete"

cancel = threading.Event()
timer = threading.Timer(0.15, cancel.set)
timer.start()
started = time.monotonic()
try:
    runtime._run_cancellable_update(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cancel,
        timeout=10,
    )
except RuntimeError as error:
    assert str(error).startswith("Update cancelled."), error
else:
    raise AssertionError("Cancelled updater returned success")
finally:
    timer.cancel()

assert time.monotonic() - started < 6
print("PASS: Control Centre can cancel its exact updater process group")
