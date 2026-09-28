#!/usr/bin/env python3
"""Classify reviewed phrases with local Qwen without executing any action."""

from statistics import median
from time import monotonic

from ovos_skill_jarvis_dispatcher.action_registry import router_catalog
from ovos_skill_jarvis_dispatcher.routing_model import classify, load_profile


CASES = (
    ("Could you start writing for me?", "text.write"),
    ("Begin continuous dictation", "dictation.start"),
    ("Pause my ongoing dictation", "dictation.pause"),
    ("Carry on dictating", "dictation.resume"),
    ("Finish dictation now", "dictation.stop"),
    ("Would you read this sentence aloud?", "reading.selection"),
    ("Please read this page twice as fast", "reading.page_fast"),
    ("I want to look something up using Firefox", "browser.search_firefox"),
    ("Can I search through Brave?", "browser.search_brave"),
    ("Can I dictate something to Hermes?", "hermes.message"),
    ("I need to tell Claude something", "claude_desktop.message"),
    ("Start a message for the Codex agent", "codex.message"),
    ("Let me ask the Claude agent something", "claude_agent.message"),
    ("Put on Get Lucky", "media.search"),
    ("Pause the music and close Firefox", "none"),
)


def main():
    profile = load_profile()
    catalogue = router_catalog(profile)
    failed = []
    times = []
    skipped = []
    for spoken, expected in CASES:
        if expected != "none" and expected not in catalogue:
            skipped.append((spoken, expected))
            continue
        started = monotonic()
        try:
            result = classify(spoken, catalogue, profile, timeout=8)
            elapsed = monotonic() - started
            actual = result["actual"]
            times.append(elapsed)
            status = "PASS" if actual == expected else "FAIL"
            print(f"{status} {elapsed:.2f}s  {spoken!r} => {actual} (expected {expected})")
            if actual != expected:
                failed.append((spoken, expected, actual))
        except Exception as error:
            elapsed = monotonic() - started
            print(f"FAIL {elapsed:.2f}s  {spoken!r} => {type(error).__name__}")
            failed.append((spoken, expected, type(error).__name__))
    for spoken, expected in skipped:
        print(f"SKIP       {spoken!r}: {expected} is disabled by this profile")
    if times:
        print(f"Median classification time: {median(times):.2f}s")
    print(f"Result: {len(CASES) - len(failed) - len(skipped)} passed, "
          f"{len(failed)} failed, {len(skipped)} profile-disabled")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
