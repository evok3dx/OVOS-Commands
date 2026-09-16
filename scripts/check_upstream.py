#!/usr/bin/env python3
"""Report whether the reviewed OVOS upstream commits have moved."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_head(repository: str) -> str:
    result = subprocess.run(
        ["git", "ls-remote", repository, "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    fields = result.stdout.strip().split()
    if len(fields) != 2 or fields[1] != "HEAD":
        raise RuntimeError(f"unexpected ls-remote response for {repository}")
    return fields[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    policy = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
    upstream = policy["upstream"]
    projects = ("installer", "workshop", "config", "core", "plugin_manager")
    results = []
    errors = False
    changed = False
    for project in projects:
        repository = upstream[f"{project}_repository"]
        reviewed = upstream[f"{project}_reference_commit"]
        try:
            current = read_head(repository)
            status = "current" if current == reviewed else "changed"
            changed = changed or status == "changed"
            results.append({
                "project": project,
                "status": status,
                "reviewed_commit": reviewed,
                "current_head": current,
                "repository": repository,
            })
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            errors = True
            results.append({
                "project": project,
                "status": "error",
                "reviewed_commit": reviewed,
                "repository": repository,
                "error": str(error),
            })

    if args.json:
        print(json.dumps({"schema_version": 1, "projects": results}, indent=2))
    else:
        for result in results:
            print(
                f"{result['status'].upper():7} {result['project']:15} "
                f"{result.get('current_head', result.get('error', 'unknown'))}"
            )
        if changed:
            print("OVOS moved since the reviewed baseline; run compatibility tests before updating it.")
        if errors:
            print("One or more upstream repositories could not be checked.")

    if errors:
        return 1
    return 2 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
