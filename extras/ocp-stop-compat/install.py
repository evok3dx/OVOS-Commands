#!/usr/bin/env python3
"""Install the reviewed Common Play STOP-1 compatibility repair."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import os
from pathlib import Path
import py_compile
import tempfile


VERSION = "1.3.10a1"
ORIGINAL_SHA256 = "f4fb671f10414ee4bfb0b88e2db4c7522876d35f95591e260c87ed9bf2840031"
MARKER = "Jarvis STOP-1 compatibility for reviewed Common Play"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_path() -> Path:
    spec = importlib.util.find_spec("ovos_plugin_common_play.ocp.player")
    if spec is None or not spec.origin:
        raise RuntimeError("Common Play player source is not installed")
    return Path(spec.origin).resolve()


def patched_source(original: bytes) -> bytes:
    text = original.decode("utf-8")
    if MARKER in text:
        if "def can_stop(self, message=None):" not in text:
            raise RuntimeError("Common Play compatibility marker is incomplete")
        return original
    if digest(original) != ORIGINAL_SHA256:
        raise RuntimeError(
            "Common Play source differs from the reviewed 1.3.10a1 file"
        )
    anchor = '''    def stop(self):
        """
        Request stopping current playback and searching
        """
'''
    replacement = '''    def can_stop(self, message=None):
        """Jarvis STOP-1 compatibility for reviewed Common Play."""
        return self.state in {PlayerState.PLAYING, PlayerState.PAUSED}

    def stop(self):
        """
        Request stopping current playback and searching
        """
'''
    if text.count(anchor) != 1:
        raise RuntimeError("Reviewed Common Play stop method was not found once")
    return text.replace(anchor, replacement, 1).encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".new", dir=path.parent
    )
    temporary = Path(name)
    compiled = temporary.with_name(temporary.name + ".pyc")
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(path.stat().st_mode & 0o777)
        py_compile.compile(str(temporary), cfile=str(compiled), doraise=True)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        compiled.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    installed = importlib.metadata.version("ovos-plugin-common-play")
    if installed != VERSION:
        raise RuntimeError(
            f"Expected ovos-plugin-common-play {VERSION}; found {installed}"
        )
    path = source_path()
    original = path.read_bytes()
    updated = patched_source(original)
    if args.check:
        print("PASS: Common Play STOP-1 compatibility source is reviewed.")
        return 0
    if updated == original:
        print("Common Play STOP-1 compatibility is already installed.")
        return 0
    atomic_write(path, updated)
    print("Installed Common Play STOP-1 compatibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
