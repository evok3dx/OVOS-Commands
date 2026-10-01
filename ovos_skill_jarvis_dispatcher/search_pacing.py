"""Local single-user pacing for provider-backed web searches."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile
import time


MINIMUM_INTERVAL = 11.0
JITTER_RANGE = (0.5, 1.0)
YOUTUBE_JITTER_RANGE = (0.5, 1.0)
MEDIA_JITTER_RANGE = (0.5, 1.0)
MAX_STATE_BYTES = 4096


class SearchCoolingDown(RuntimeError):
    """A recent provider-backed search must finish before another starts."""

    def __init__(self, remaining: float):
        self.remaining = max(0.0, float(remaining))
        super().__init__(f"search cooldown has {self.remaining:.1f} seconds remaining")


def _read_state(path: Path) -> dict[str, float]:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_size > MAX_STATE_BYTES):
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {}
        return {key: float(item) for key, item in value.items()
                if isinstance(key, str) and isinstance(item, (int, float))}
    except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def _write_state(path: Path, value: dict[str, object]) -> None:
    descriptor, temporary = tempfile.mkstemp(
        prefix=".search-pacing.", dir=path.parent,
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, sort_keys=True, separators=(",", ":"))
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def pace_search(provider: str, *, state_root: Path | None = None,
                clock=time.time, sleeper=time.sleep, jitter: float | None = None) -> float:
    """Reserve one provider-backed search and apply its bounded pre-delay.

    The shared timestamp prevents concurrent browser and YouTube submissions.
    It deliberately does not retry, rotate networks or answer a provider
    challenge. Media title lookup retains the brief pre-delay and a short
    post-result transition before opening the browser. ``provider`` is retained
    only for local diagnostics.
    """
    if not isinstance(provider, str) or not provider.isascii() or not provider.isalpha():
        raise ValueError("invalid search provider")
    root = state_root or (Path.home() / ".local/state/jarvis")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        root.chmod(0o700)
    except OSError:
        pass

    lock_path = root / "search-pacing.lock"
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    lock_descriptor = os.open(lock_path, flags, 0o600)
    try:
        os.fchmod(lock_descriptor, 0o600)
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
        state_path = root / "search-pacing.json"
        state = _read_state(state_path)
        now = float(clock())
        previous = state.get("last_reserved", 0.0)
        remaining = previous + MINIMUM_INTERVAL - now
        if remaining > 0:
            raise SearchCoolingDown(remaining)
        if provider == "media":
            interval = MEDIA_JITTER_RANGE
        elif provider == "youtube":
            interval = YOUTUBE_JITTER_RANGE
        else:
            interval = JITTER_RANGE
        delay = (secrets.SystemRandom().uniform(*interval)
                 if jitter is None else float(jitter))
        if not interval[0] <= delay <= interval[1]:
            raise ValueError("invalid search pacing delay")
        state = {
            "last_reserved": now + delay,
            "provider": provider,
        }
        _write_state(state_path, state)
    finally:
        os.close(lock_descriptor)

    if delay:
        sleeper(delay)
    return delay
