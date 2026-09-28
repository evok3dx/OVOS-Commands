#!/usr/bin/env python3
"""Run 300+ non-executing command variations through the local Qwen router.

The benchmark never dispatches an action. It checks request-specific policy
coverage first, then asks the configured local model to select an allowlisted
action. Typed text starts after STT, so Whisper still needs a separate live
microphone check.
"""

import argparse
import math
import platform
import statistics
import subprocess
import sys
import types
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

WRAPPERS = (
    "{}",
    "Please {}",
    "Could you {} for me",
    "Would you kindly {}",
)

# Four variations of 90 imperative bases produce 360 deterministic cases.
BASE_CASES = {
    "text.write": (
        "write this", "type this", "write something here",
        "type a short note here", "take down what I say",
    ),
    "dictation.start": (
        "start writing", "begin continuous dictation", "start dictating",
        "begin writing continuously", "turn on continuous writing",
    ),
    "dictation.pause": (
        "pause dictation", "pause my ongoing dictation", "hold dictation",
        "pause continuous writing", "temporarily stop writing",
    ),
    "dictation.resume": (
        "resume dictation", "carry on dictating", "continue writing",
        "resume continuous writing", "keep taking dictation",
    ),
    "dictation.stop": (
        "stop dictation", "finish dictation now", "stop writing",
        "end continuous writing", "finish taking dictation",
    ),
    "system.show_desktop": (
        "show desktop", "go to the desktop", "minimize all windows",
        "hide every window", "take me to the desktop",
    ),
    "reading.selection": (
        "read this", "read this text", "read this sentence aloud",
        "read the selected text", "speak this selection",
    ),
    "reading.selection_fast": (
        "read this at 2x", "read this text twice as fast",
        "read the selection at double speed", "speak this sentence two x",
        "read the selected text two times speed",
    ),
    "reading.page": (
        "read this page", "read the current webpage", "read this window",
        "speak the article on screen", "read the whole page aloud",
    ),
    "reading.page_fast": (
        "read this page at 2x", "read the webpage twice as fast",
        "read this article at double speed", "speak this page two x",
        "read the current screen two times speed",
    ),
    "browser.search_firefox": (
        "search using Firefox", "look something up in Firefox",
        "search the web with Firefox", "start a Firefox search",
        "look this up using Firefox",
    ),
    "browser.search_brave": (
        "search using Brave", "look something up in Brave",
        "search the web with Brave", "start a Brave search",
        "look this up using Brave",
    ),
    "hermes.message": (
        "message Hermes", "dictate something to Hermes",
        "start a message in Hermes", "tell Hermes something",
        "compose a Hermes message",
    ),
    "claude_desktop.message": (
        "message Claude", "dictate something to Claude",
        "start a message in Claude", "tell Claude something",
        "compose a Claude message",
    ),
    "media.search": (
        "play Get Lucky", "put on Teardrop", "find and play Imagine",
        "spin up the track Dreams", "play the song Heroes",
    ),
    "files.search": (
        "find the project plan file", "locate the holiday budget document",
        "search my files for meeting notes", "look for the invoice folder",
        "find the presentation named quarterly review",
    ),
    "none": (
        "pause music and close Firefox", "message Hermes and Claude",
        "delete every document", "run an arbitrary shell command",
        "open Firefox after closing Brave", "send my password online",
        "do the unusual thing", "purple bananas now",
        "read my last text twice as fast", "search without telling me where",
    ),
}


def cases():
    result = []
    seen = set()
    for expected, bases in BASE_CASES.items():
        for base in bases:
            for wrapper in WRAPPERS:
                phrase = wrapper.format(base)
                key = phrase.casefold()
                if key in seen:
                    raise AssertionError(f"Duplicate generated phrase: {phrase}")
                seen.add(key)
                result.append((phrase, expected))
    if len(result) < 300:
        raise AssertionError("Benchmark must contain at least 300 variations")
    return result


def percentile(values, percent):
    if not values:
        return None
    ordered = sorted(values)
    position = math.ceil(percent / 100 * len(ordered)) - 1
    return ordered[min(len(ordered) - 1, max(0, position))]


def service_state(name):
    result = subprocess.run(
        ["systemctl", "--user", "is-active", name],
        text=True, capture_output=True, check=False,
    )
    return result.stdout.strip() or "unknown"


def safe_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(path, records, total, profile, catalogue, started_at, interrupted,
                 model, router_enabled):
    model_records = [record for record in records
                     if record.get("seconds") is not None]
    passed = sum(record["status"] == "PASS" for record in records)
    failures = [record for record in records if record["status"] == "FAIL"]
    skipped = [record for record in records if record["status"] == "SKIP"]
    timings = [record["seconds"] for record in model_records]
    timeouts = sum(record.get("actual") == "TimeoutError" for record in records)
    by_action = defaultdict(Counter)
    for record in records:
        by_action[record["expected"]][record["status"]] += 1

    lines = [
        "# Jarvis non-executing routing benchmark", "",
        f"- Started: `{started_at.isoformat()}`",
        f"- Finished: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Host: `{platform.node() or 'local'}` / `{platform.machine()}`",
        f"- Model: `{model}`",
        f"- Router enabled: `{router_enabled}`",
        f"- Profile mode: `{profile.get('mode', 'custom')}`",
        f"- Allowlisted router actions: `{len(catalogue)}`",
        f"- Generated variations: `{total}`",
        f"- Completed: `{len(records)}`{' (interrupted)' if interrupted else ''}",
        f"- Pass / fail / skipped: `{passed}` / `{len(failures)}` / `{len(skipped)}`",
        f"- Timeouts: `{timeouts}`", "", "## Scope", "",
        "This report tests typed text after speech recognition. It verifies the",
        "request-specific allowlist and the real local Qwen selection without",
        "executing any action. It does **not** test Whisper, the microphone, wake",
        "word, focused-window dispatch, typing, or application launch. Those remain",
        "separate live acceptance tests.", "", "## Runtime", "",
    ]
    if timings:
        lines += [
            f"- Median: `{statistics.median(timings):.2f}s`",
            f"- P95: `{percentile(timings, 95):.2f}s`",
            f"- Slowest: `{max(timings):.2f}s`",
        ]
    else:
        lines.append("- No model calls completed.")
    lines += ["", "## Results by action", "",
              "| Expected | Pass | Fail | Skip |", "|---|---:|---:|---:|"]
    for action in sorted(by_action):
        counts = by_action[action]
        lines.append(
            f"| `{action}` | {counts['PASS']} | {counts['FAIL']} | {counts['SKIP']} |")
    lines += ["", "## Failures", ""]
    if not failures:
        lines.append("None in the completed set.")
    else:
        lines += ["| Phrase | Expected | Actual | Seconds | Candidates |",
                  "|---|---|---|---:|---:|"]
        for record in failures:
            lines.append("| " + " | ".join((
                safe_cell(record["phrase"]), f"`{record['expected']}`",
                f"`{record['actual']}`", f"{record.get('seconds') or 0:.2f}",
                str(record.get("candidates", 0)),
            )) + " |")
    if skipped:
        lines += ["", "## Profile-disabled groups", ""]
        counts = Counter(record["expected"] for record in skipped)
        for action, count in sorted(counts.items()):
            lines.append(f"- `{action}`: {count} cases (not enabled in this profile)")
    lines += ["", "## Release interpretation", "",
              "- Candidate-policy failures are code/configuration defects, not model accuracy issues.",
              "- Wrong allowed actions are model/prompt accuracy failures.",
              "- Timeouts are performance failures at the configured deadline.",
              "- A passing row does not prove Whisper heard the phrase correctly.",
              "- Do not broaden risky actions to improve this score; they must remain strict.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=8.0,
                        help="Per-case model deadline (default: live 8 seconds)")
    parser.add_argument("--quick", action="store_true",
                        help="Run an evenly distributed 40-case model sample")
    parser.add_argument("--policy-only", action="store_true",
                        help="Check all candidate allowlists without calling Qwen")
    parser.add_argument("--output", type=Path,
                        help="Markdown report path (default: Jarvis state reports)")
    args = parser.parse_args()
    if not 0 < args.timeout <= 120:
        parser.error("--timeout must be between 0 and 120 seconds")

    # Load the routing modules without importing the live OVOS skill class.
    # This keeps --policy-only usable from an extracted release before the
    # installer has created the OVOS virtualenv and cannot start any service.
    root = Path(__file__).resolve().parents[1]
    package = types.ModuleType("ovos_skill_jarvis_dispatcher")
    package.__path__ = [str(root / "ovos_skill_jarvis_dispatcher")]
    sys.modules[package.__name__] = package

    from ovos_skill_jarvis_dispatcher.action_registry import router_catalog
    from ovos_skill_jarvis_dispatcher.routing_model import (
        MODEL, candidates_for, classify, load_profile,
    )
    from ovos_skill_jarvis_dispatcher.profile import (
        REFERENCE_COMPATIBILITY_PROFILE, resolve_profile,
    )
    from ovos_skill_jarvis_dispatcher.routing_runtime import settings

    suite = cases()
    if args.quick:
        indexes = {round(i * (len(suite) - 1) / 39) for i in range(40)}
        selected = [case for index, case in enumerate(suite) if index in indexes]
    else:
        selected = suite
    capabilities = Path.home() / ".config/jarvis/capabilities.json"
    legacy_profile = Path.home() / ".config/jarvis/profile.json"
    if args.policy_only and not capabilities.is_file() and not legacy_profile.is_file():
        profile = resolve_profile(REFERENCE_COMPATIBILITY_PROFILE)
    else:
        profile = load_profile()
    catalogue = router_catalog(profile)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output = args.output or (Path.home() / "Downloads" /
                             f"routing-benchmark-{timestamp}.md")
    started_at = datetime.now(timezone.utc)
    records = []
    interrupted = False

    print(f"Jarvis router benchmark: {len(selected)} of {len(suite)} variations")
    print("No actions will be executed.")
    print("Services:", ", ".join(
        f"{name}={service_state(name)}" for name in
        ("ovos-listener.service", "ovos-core.service", "ovos-audio.service")))
    try:
        for index, (phrase, expected) in enumerate(selected, 1):
            allowed = candidates_for(phrase, catalogue, profile)
            unavailable = expected != "none" and expected not in catalogue
            policy_ok = expected == "none" or expected in allowed
            record = {"phrase": phrase, "expected": expected,
                      "candidates": len(allowed), "seconds": None}
            if unavailable:
                record.update(status="SKIP", actual="profile-disabled")
            elif not policy_ok:
                record.update(status="FAIL", actual="policy-missing")
            elif args.policy_only:
                record.update(status="PASS", actual="policy-covered")
            else:
                began = monotonic()
                try:
                    result = classify(phrase, catalogue, profile,
                                      timeout=args.timeout)
                    actual = result["actual"]
                except Exception as error:
                    actual = type(error).__name__
                record["seconds"] = monotonic() - began
                record.update(status="PASS" if actual == expected else "FAIL",
                              actual=actual)
            records.append(record)
            elapsed = ("" if record["seconds"] is None
                       else f" {record['seconds']:.2f}s")
            print(f"[{index:03d}/{len(selected):03d}] {record['status']}{elapsed} "
                  f"{phrase!r} => {record['actual']} (expected {expected})",
                  flush=True)
    except KeyboardInterrupt:
        interrupted = True
        print("\nInterrupted; writing a partial report.")
    finally:
        write_report(output, records, len(suite), profile, catalogue,
                     started_at, interrupted, MODEL, settings())
        print(f"Report: {output}")

    failures = sum(record["status"] == "FAIL" for record in records)
    return 130 if interrupted else (1 if failures else 0)


if __name__ == "__main__":
    raise SystemExit(main())
