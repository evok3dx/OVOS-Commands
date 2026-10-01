#!/usr/bin/env python3
"""Verify shared browser/YouTube pacing without network or desktop access."""

import json
import sys
import tempfile
import types
from pathlib import Path


root = Path(__file__).resolve().parents[1]
package = types.ModuleType("ovos_skill_jarvis_dispatcher")
package.__path__ = [str(root / "ovos_skill_jarvis_dispatcher")]
sys.modules[package.__name__] = package

from ovos_skill_jarvis_dispatcher.search_pacing import (  # noqa: E402
    SearchCoolingDown, pace_search,
)


with tempfile.TemporaryDirectory() as temporary:
    state_root = Path(temporary) / "state"
    slept = []
    delay = pace_search(
        "youtube", state_root=state_root, clock=lambda: 100.0,
        sleeper=slept.append, jitter=1.0,
    )
    assert delay == 1.0 and slept == [1.0]
    state = json.loads((state_root / "search-pacing.json").read_text())
    assert state == {"last_reserved": 101.0, "provider": "youtube"}
    assert state_root.stat().st_mode & 0o777 == 0o700
    assert (state_root / "search-pacing.json").stat().st_mode & 0o777 == 0o600
    assert (state_root / "search-pacing.lock").stat().st_mode & 0o777 == 0o600

    # Media starts its lookup immediately. It keeps the shared anti-burst
    # reservation and applies its deliberate transition only after a result.
    media_root = Path(temporary) / "media-state"
    media_slept = []
    delay = pace_search(
        "media", state_root=media_root, clock=lambda: 200.0,
        sleeper=media_slept.append, jitter=0.0,
    )
    assert delay == 0.0 and media_slept == []
    media_state = json.loads((media_root / "search-pacing.json").read_text())
    assert media_state == {"last_reserved": 200.0, "provider": "media"}

    try:
        pace_search(
            "browser", state_root=state_root, clock=lambda: 105.0,
            sleeper=slept.append, jitter=1.0,
        )
    except SearchCoolingDown as error:
        assert 7.9 < error.remaining < 8.1
    else:
        raise AssertionError("A burst search bypassed the shared cooldown")

    # Browser and YouTube share the same reservation timeline. A later normal
    # request receives only the bounded local pacing delay.
    pace_search(
        "browser", state_root=state_root, clock=lambda: 116.0,
        sleeper=slept.append, jitter=0.5,
    )
    assert slept == [1.0, 0.5]

    try:
        pace_search(
            "youtube-unsafe", state_root=state_root, clock=lambda: 200.0,
            sleeper=slept.append, jitter=1.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid provider label was accepted")

print("PASS: browser and YouTube searches share bounded local pacing")
