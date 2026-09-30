#!/usr/bin/env python3
"""Reject incomplete or mixed OVOS environments before a live swap."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path


REQUIRED_ENTRY_POINTS = {
    ("opm.microphone", "ovos-microphone-plugin-sounddevice"),
    ("opm.stt", "ovos-stt-plugin-fasterwhisper"),
    ("opm.tts", "ovos-tts-plugin-phoonnx"),
    ("opm.wake_word", "ovos-ww-plugin-openwakeword"),
}
REQUIRED_LAUNCHERS = (
    "ovos-audio", "ovos-core", "ovos-dinkum-listener", "ovos-listen",
    "ovos-messagebus", "ovos-say-to", "ovos-speak",
)


def unexpected_pip_check_lines(report: str) -> list[str]:
    """Return every dependency failure; the V4 candidate has no exemptions."""
    return [line for line in (item.strip() for item in report.splitlines())
            if line]


def validate_versions(manifest: Path) -> None:
    expected = json.loads(manifest.read_text(encoding="utf-8"))["packages"]
    failures = []
    for name, wanted in expected.items():
        try:
            actual = metadata.version(name)
        except metadata.PackageNotFoundError:
            failures.append(f"{name}: missing (expected {wanted})")
        else:
            if actual != wanted:
                failures.append(f"{name}: {actual} (expected {wanted})")
    if failures:
        raise SystemExit("Reviewed OVOS package mismatch:\n" + "\n".join(failures))


def entry_point_pairs(points: object) -> set[tuple[str, str]]:
    """Normalise both current and legacy importlib.metadata return shapes."""
    if isinstance(points, Mapping):
        return {
            (str(group), entry.name)
            for group, entries in points.items()
            for entry in entries
        }
    return {(entry.group, entry.name) for entry in points}


def validate_entry_points() -> None:
    available = entry_point_pairs(metadata.entry_points())
    missing = sorted(REQUIRED_ENTRY_POINTS - available)
    if missing:
        rendered = "\n".join(f"{group}: {name}" for group, name in missing)
        raise SystemExit(f"Required OVOS entry points are missing:\n{rendered}")


def validate_launchers() -> None:
    bindir = Path(sys.prefix) / "bin"
    expected = {
        f"#!{bindir / 'python'}",
        f"#!{bindir / f'python{sys.version_info.major}'}",
        f"#!{bindir / f'python{sys.version_info.major}.{sys.version_info.minor}'}",
    }
    failures = []
    for name in REQUIRED_LAUNCHERS:
        launcher = bindir / name
        if not launcher.is_file() or launcher.stat().st_size == 0:
            failures.append(f"{name}: missing or empty")
            continue
        first = launcher.open("rb").readline().decode("utf-8", "replace").strip()
        if first not in expected:
            failures.append(f"{name}: unsafe interpreter {first!r}")
    if failures:
        raise SystemExit("Invalid staged OVOS launchers:\n" + "\n".join(failures))


def validate_dependencies() -> None:
    result = subprocess.run([sys.executable, "-m", "pip", "check"],
                            check=False, capture_output=True, text=True)
    if result.returncode == 0:
        return
    report = "\n".join(part.strip() for part in (result.stdout, result.stderr)
                       if part.strip())
    unexpected = unexpected_pip_check_lines(report)
    if unexpected:
        raise SystemExit("The clean OVOS environment has unresolved dependencies:\n"
                         + "\n".join(unexpected))
    raise SystemExit('Dependency validation failed without a usable report.')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    validate_versions(args.manifest)
    validate_dependencies()
    validate_entry_points()
    validate_launchers()
    print("Clean OVOS environment matches the reviewed package set.")


if __name__ == "__main__":
    main()
