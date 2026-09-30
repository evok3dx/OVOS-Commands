#!/usr/bin/env python3
"""Run 350 balanced, non-executing commands through the local Qwen router.

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

CORE_CASES = {
    "system.show_desktop": ("show the desktop", "please minimise all windows", "take me to the desktop", "could you hide every window"),
    "media.play": ("resume the music", "please resume playback", "carry on playing", "could you start playback again"),
    "media.pause": ("pause the music", "please pause playback", "hold the current track", "could you pause what is playing"),
    "media.stop": ("stop the music", "please stop playback", "end the current track", "could you stop what is playing"),
    "media.next": ("skip to the next track", "please skip to the next song", "move on to the next one", "could you go to the following track"),
    "media.previous": ("go to the previous track", "please go back one song", "return to the last track", "could you go to the song before this"),
    "media.search": ("play Get Lucky", "please put on Teardrop", "find and play Imagine", "could you play the song Heroes"),
    "media.prompt": ("play some music", "please put some tunes on", "I would like to choose some music", "could you ask me what to play"),
    "hermes.message": ("message Hermes", "please tell Hermes something", "start a message in Hermes", "could you let me dictate to Hermes"),
    "window.minimize": ("minimise this app", "please minimize this application", "hide the window I am using", "could you minimise the focused window"),
    "window.maximize": ("maximise this application", "please maximize this app", "make the active window bigger", "could you maximise the focused window"),
    "window.restore": ("restore this app", "please return the current window to normal", "unmaximise this application", "could you restore the focused window"),
    "reading.last_typed": ("read it back", "please read my last text", "read the last text", "could you read that back to me"),
    "reading.selection": ("read this", "please read the selected text", "speak this selection aloud", "could you read this sentence to me"),
    "reading.selection_fast": ("read this at 2x", "please read the selection twice as fast", "speak this text at double speed", "could you read this sentence two times speed"),
    "reading.page": ("read this page", "please read the current webpage", "speak the article on screen", "could you read this window aloud"),
    "reading.page_fast": ("read this page at 2x", "please read the webpage twice as fast", "speak this article at double speed", "could you read the current screen two times speed"),
    "text.write": ("write this", "please type something here", "take down what I say", "could you write a short note here"),
    "dictation.start": ("start dictation", "please begin continuous writing", "start writing continuously", "could you turn on dictation"),
    "dictation.pause": ("pause dictation", "please hold continuous writing", "temporarily stop taking dictation", "could you pause my ongoing dictation"),
    "dictation.resume": ("resume dictation", "please continue continuous writing", "carry on taking dictation", "could you resume my ongoing dictation"),
    "dictation.stop": ("stop dictation", "please finish continuous writing", "end my ongoing dictation", "could you stop taking dictation"),
    "browser.scroll_down": ("scroll down", "please move down the page", "scroll this page lower", "could you go down a little"),
    "browser.scroll_up": ("scroll up", "please move up the page", "scroll this page higher", "could you go up a little"),
    "browser.page_down": ("page down", "please move down one page", "go to the next screenful", "could you page down once"),
    "browser.page_up": ("page up", "please move up one page", "go to the previous screenful", "could you page up once"),
    "browser.top": ("go to the top", "please jump to the top of the page", "take me to the page beginning", "could you scroll all the way up"),
    "browser.bottom": ("go to the bottom", "please jump to the bottom of the page", "take me to the page end", "could you scroll all the way down"),
    "browser.back": ("go back", "please return to the previous page", "take me back one page", "could you navigate backwards"),
    "browser.forward": ("go forward", "please return to the next page", "take me forward one page", "could you navigate forwards"),
    "browser.new_tab": ("open a new tab", "please make another tab", "start a fresh tab", "could you create a new tab"),
    "browser.refresh": ("refresh the page", "please reload this webpage", "load the current page again", "could you refresh this tab"),
    "browser.address": ("focus the address bar", "please let me enter a web address", "put the cursor in the location bar", "could you select the address bar"),
    "browser.search_brave": ("search with Brave", "please look something up in Brave", "start a Brave web search", "could you search the internet using Brave"),
    "browser.search_firefox": ("search with Firefox", "please look something up in Firefox", "start a Firefox web search", "could you search the internet using Firefox"),
    "browser.search_youtube": ("search YouTube", "please look something up on YouTube", "start a YouTube search", "could you find a video on YouTube"),
    "browser.youtube_shorts": ("open YouTube Shorts", "please show me YouTube Shorts", "take me to the Shorts page", "could you launch YouTube Shorts"),
    "files.search": ("find the project plan file", "please locate the holiday budget document", "search my files for meeting notes", "could you look for the invoice folder"),
    "notes.new": ("create a new memo", "please start another memo", "make me a blank memo", "could you open a fresh memo"),
    "notes.search": ("search my notes", "please find something in my notes", "look through the notes", "could you start a notes search"),
    "mail.new": ("compose a new message", "please start a fresh message", "compose a fresh message", "could you compose a blank message"),
    "mail.search": ("search Proton Mail", "please find something in Proton Mail", "look through Proton Mail", "could you start a Proton Mail search"),
    "codex.message": ("message the Codex agent", "please tell Codex something", "start a message to the Codex agent", "could you let me dictate to Codex"),
    "claude_agent.message": ("message the Claude agent", "please tell the Claude agent something", "start a message to the Claude agent", "could you let me dictate to the Claude agent"),
    "claude_desktop.message": ("message Claude", "please tell Claude something", "start a message in Claude Desktop", "could you let me dictate to Claude"),
    "response.read_latest": ("read the latest response", "please read the newest answer", "speak the last assistant reply", "could you read the most recent response"),
    "date.today": ("what is today's date", "please tell me the date today", "read today's date", "could you say what date it is"),
}

APPLICATIONS = {
    "brave": "Brave", "firefox": "Firefox", "signal": "Signal",
    "zoom": "Zoom", "terminal": "Terminal", "notes": "Notes",
    "office": "OnlyOffice", "claude": "Claude", "chatgpt": "ChatGPT",
    "hermes": "Hermes", "mail": "system default mail", "proton_mail": "Proton Mail",
    "calendar": "Calendar",
}

REJECTION_CASES = (
    "pause music and close Firefox",
    "message Hermes and Claude",
    "delete every document",
    "run an arbitrary shell command",
    "open Firefox after closing Brave",
    "send my password online",
)


def cases():
    result = []
    seen = set()
    for expected, phrases in CORE_CASES.items():
        result.extend((phrase, expected) for phrase in phrases)
    for app_id, name in APPLICATIONS.items():
        variants = {
            "open": (f"open {name}", f"please launch {name}", f"could you start {name} for me"),
            "focus": (f"focus {name}", f"please bring {name} to the front", f"could you switch to {name}"),
            "minimize": (f"minimise {name}", f"please minimise the {name} window", f"could you hide {name} for me"),
            "maximize": (f"maximise {name}", f"please maximise the {name} window", f"could you make {name} fill the screen"),
        }
        for operation, phrases in variants.items():
            expected = f"application.{operation}.{app_id}"
            result.extend((phrase, expected) for phrase in phrases)
    result.extend((phrase, "none") for phrase in REJECTION_CASES)
    for phrase, _expected in result:
        key = phrase.casefold()
        if key in seen:
            raise AssertionError(f"Duplicate generated phrase: {phrase}")
        seen.add(key)
    if len(result) != 350:
        raise AssertionError(
            f"Benchmark must contain exactly 350 variations, got {len(result)}"
        )
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
                 model, router_enabled, policy_only=False):
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
        f"- Architecture: `{platform.machine()}`",
        f"- Mode: `{'policy only, no model calls' if policy_only else 'local model selection'}`",
        f"- Model: `{model}`",
        f"- Router enabled: `{router_enabled}`",
        f"- Profile mode: `{profile.get('mode', 'custom')}`",
        f"- Allowlisted router actions: `{len(catalogue)}`",
        f"- Generated variations: `{total}`",
        f"- Completed: `{len(records)}`{' (interrupted)' if interrupted else ''}",
        f"- Pass / fail / skipped: `{passed}` / `{len(failures)}` / `{len(skipped)}`",
        f"- Timeouts: `{timeouts}`", "", "## Scope", "",
        "This report tests typed text after speech recognition. It verifies the",
        ("request-specific allowlist only, with no local model calls, without" if policy_only else
         "request-specific allowlist and the real local Qwen selection without"),
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
                     started_at, interrupted, MODEL, settings(), args.policy_only)
        print(f"Report: {output}")

    failures = sum(record["status"] == "FAIL" for record in records)
    return 130 if interrupted else (1 if failures else 0)


if __name__ == "__main__":
    raise SystemExit(main())
