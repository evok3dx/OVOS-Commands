#!/usr/bin/env python3
"""Create a privacy-first Jarvis diagnostic bundle for a coding AI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (
    ".github",
    "command_editor",
    "docs",
    "mic",
    "ovos_skill_jarvis_dispatcher",
    "profiles",
    "scripts",
    "system_helpers",
    "systemd",
    "tray",
)
SOURCE_FILES = (
    ".gitignore",
    "COMMAND-EDITOR.md",
    "README.md",
    "compatibility.json",
    "deployment-manifest.json",
    "pyproject.toml",
)
EXCLUDED_PARTS = {".git", "__pycache__", "dist", "history"}
EXCLUDED_SUFFIXES = {".pyc", ".log", ".wav", ".mp3", ".flac"}
SERVICES = (
    "ovos.service",
    "ovos-messagebus.service",
    "ovos-core.service",
    "ovos-listener.service",
    "ovos-audio.service",
    "ovos-phal.service",
)


def project_version() -> str:
    source = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', source, re.MULTILINE)
    return match.group(1) if match else "unknown"


def sanitise(text: str, home: Path) -> str:
    """Redact common identity and credential material from collected output."""

    value = text.replace(str(ROOT), "<repository>")
    value = value.replace(str(home), "~")
    username = os.environ.get("USER") or os.environ.get("LOGNAME")
    if username and len(username) > 2:
        value = re.sub(rf"(?<![\w-]){re.escape(username)}(?![\w-])", "<user>", value)
    value = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "<redacted-email>",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"(?i)\b(api[_-]?key|access[_-]?token|authorization|password|secret)"
        r"\s*[:=]\s*[^\s,;]+",
        r"\1=<redacted>",
        value,
    )
    value = re.sub(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", value)
    return value


def display_command(command: list[str], home: Path) -> list[str]:
    displayed = []
    for item in command:
        value = str(item)
        if value == sys.executable:
            value = "python3"
        value = sanitise(value, home)
        displayed.append(value)
    return displayed


def run(command: list[str], home: Path, timeout: int = 30) -> dict[str, object]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return {
            "command": display_command(command, home),
            "returncode": result.returncode,
            "stdout": sanitise(result.stdout, home),
            "stderr": sanitise(result.stderr, home),
        }
    except (OSError, subprocess.SubprocessError) as error:
        return {
            "command": display_command(command, home),
            "returncode": 127,
            "stdout": "",
            "stderr": sanitise(str(error), home),
        }


def copy_source(destination: Path) -> dict[str, int]:
    copied = 0
    copied_bytes = 0
    skipped = 0
    candidates: list[Path] = []
    for relative in SOURCE_FILES:
        path = ROOT / relative
        if path.is_file():
            candidates.append(path)
    for relative in SOURCE_ROOTS:
        root = ROOT / relative
        if root.is_dir():
            candidates.extend(
                path for path in root.rglob("*")
                if path.is_file() and not path.is_symlink()
            )

    for source in sorted(set(candidates)):
        relative = source.relative_to(ROOT)
        if EXCLUDED_PARTS.intersection(relative.parts):
            skipped += 1
            continue
        if source.suffix.lower() in EXCLUDED_SUFFIXES:
            skipped += 1
            continue
        size = source.stat().st_size
        if size > 2_000_000 or copied_bytes + size > 20_000_000:
            skipped += 1
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
        copied_bytes += size
    return {"files": copied, "bytes": copied_bytes, "skipped": skipped}


def ovos_versions(home: Path) -> dict[str, object]:
    ovos_python = Path(os.environ.get("OVOS_PYTHON", home / ".venvs/ovos/bin/python"))
    if not ovos_python.is_file():
        return {"available": False, "expected_python": "~/.venvs/ovos/bin/python"}
    probe = r'''
import importlib.metadata as metadata
import json
import sys

names = [
    "ovos-core", "ovos-workshop", "ovos-config", "ovos-plugin-manager",
    "ovos-messagebus", "ovos-audio", "ovos-dinkum-listener",
    "ovos-skill-jarvis-dispatcher"
]
versions = {}
for name in names:
    try:
        versions[name] = metadata.version(name)
    except metadata.PackageNotFoundError:
        versions[name] = None
print(json.dumps({"python": sys.version.split()[0], "packages": versions}))
'''
    result = run([str(ovos_python), "-c", probe], home)
    if result["returncode"] != 0:
        return {"available": True, "probe_error": result["stderr"]}
    try:
        return {"available": True, **json.loads(str(result["stdout"]))}
    except json.JSONDecodeError as error:
        return {"available": True, "probe_error": str(error)}


def service_state(home: Path) -> dict[str, object]:
    if shutil.which("systemctl") is None or os.environ.get("JARVIS_TEST_MODE") == "1":
        return {"available": False, "reason": "systemctl unavailable or test mode"}
    states: dict[str, object] = {}
    for service in SERVICES:
        result = run(
            [
                "systemctl", "--user", "show", service,
                "--property=LoadState,ActiveState,SubState,UnitFileState",
            ],
            home,
            timeout=10,
        )
        fields = {}
        for line in str(result["stdout"]).splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                fields[key] = value
        states[service] = fields or {"query_error": result["stderr"]}
    return {"available": True, "units": states}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(bundle: Path) -> None:
    entries = []
    for path in sorted(item for item in bundle.rglob("*") if item.is_file()):
        if path.name == "MANIFEST.sha256":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(f"{digest}  {path.relative_to(bundle).as_posix()}")
    (bundle / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def private_tar_info(member: tarfile.TarInfo) -> tarfile.TarInfo:
    """Keep extracted support-bundle contents private by default."""

    member.uid = 0
    member.gid = 0
    member.uname = ""
    member.gname = ""
    member.mode = 0o700 if member.isdir() else 0o600
    return member


def collect_logs(bundle: Path, home: Path) -> None:
    unit_arguments = [
        item
        for service in SERVICES
        for item in ("--unit", service)
    ]
    result = run(
        [
            "journalctl", "--user", "--no-pager", "--since=-24 hours",
            "--priority=warning", "--lines=200",
            *unit_arguments,
        ],
        home,
        timeout=20,
    )
    (bundle / "OPTIONAL_SANITISED_LOGS.txt").write_text(
        str(result["stdout"]) + str(result["stderr"]),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    issue = parser.add_mutually_exclusive_group()
    issue.add_argument("--issue", help="Short description of the problem")
    issue.add_argument("--issue-file", type=Path, help="Read the problem description from a file")
    parser.add_argument("--profile", default=os.environ.get("JARVIS_PROFILE"))
    parser.add_argument("--output", type=Path, help="Output .tar.gz path")
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Include sanitised warning logs; may still contain sensitive context",
    )
    args = parser.parse_args()

    home = Path(os.environ.get("JARVIS_HOME", str(Path.home()))).expanduser().resolve()
    if args.issue_file:
        issue_text = args.issue_file.read_text(encoding="utf-8")
    else:
        issue_text = args.issue or "No issue description was supplied. Review the diagnostics and identify actionable problems."
    issue_text = sanitise(issue_text.strip(), home)
    if len(issue_text.encode("utf-8")) > 100_000:
        parser.error("issue description exceeds the 100 KB privacy and size limit")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    default_directory = home / "Downloads"
    if not default_directory.is_dir():
        default_directory = Path.cwd()
    output = args.output or default_directory / f"jarvis-ai-report-{timestamp}.tar.gz"
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        parser.error(f"refusing to overwrite existing output: {output}")

    with tempfile.TemporaryDirectory(prefix="jarvis-ai-report-") as temporary:
        bundle = Path(temporary) / f"jarvis-ai-report-{timestamp}"
        source = bundle / "source"
        diagnostics = bundle / "diagnostics"
        source.mkdir(parents=True)
        diagnostics.mkdir(parents=True)

        source_inventory = copy_source(source)
        (bundle / "ISSUE.md").write_text(f"# Reported issue\n\n{issue_text}\n", encoding="utf-8")
        (bundle / "AI_INSTRUCTIONS.md").write_text(
            """# Jarvis AI maintenance handoff

This bundle is a privacy-first diagnostic snapshot for the OVOS Jarvis command
repository. Start with `ISSUE.md`, then inspect `diagnostics/report.json`, the
check results, and `source/`.

## Your task

1. Reproduce or identify the most likely root cause using only evidence here.
2. Preserve all security invariants and existing spoken-command behaviour.
3. Make the smallest maintainable fix in `source/`.
4. Run or reason through the documented validation commands.
5. Return a unified Git patch plus `PATCH_NOTES.md` containing the root cause,
   changed files, tests, risks, and rollback notes.

If evidence is insufficient, state exactly which privacy-safe diagnostic is
missing. Do not request credentials, raw voice recordings, clipboard contents,
private messages, agent prompts, or unrestricted system access.

## Non-negotiable boundaries

- Never add arbitrary shell execution or user-configurable executable paths.
- Keep application and action selection allowlisted.
- Never weaken focused-window, confirmation, agent-account, Hermes-container,
  localhost-messagebus, or no-root runtime boundaries.
- Never add secrets or tokens to source, logs, examples, or patches.
- Do not alter sudoers, privileged helpers, update trust, or signature policy
  unless the reported issue explicitly concerns that area; flag such changes
  for separate human security review.
- Do not silently update OVOS dependencies or replace the supported platform.

## Validation contract

The proposed patch should keep these commands passing:

```bash
python3 scripts/validate_refactor.py
bash scripts/test-deployment.sh
bash scripts/build-release.sh
```

Do not apply or deploy the patch. The Jarvis owner will validate it in a staged
environment and retain the existing rollback point.
""",
            encoding="utf-8",
        )
        (bundle / "CONTENTS.md").write_text(
            """# Bundle contents and privacy boundary

Included by allowlist:

- the repository source needed to diagnose and patch Jarvis;
- the issue description supplied to `jarvis-report`;
- repository validation and read-only compatibility results;
- selected package versions and user-service states;
- a SHA-256 manifest for accidental-corruption detection.

Excluded by default:

- environment variables and command history;
- raw OVOS logs and recognised utterances;
- audio, transcripts, clipboard data and typed text;
- messages, prompts, responses, credentials and personal files;
- hostname, IP addresses, Git remotes and account identifiers.

The SHA-256 manifest is not a digital signature. Treat the archive as private,
inspect it before sharing, and share it only with the intended recipient.
""",
            encoding="utf-8",
        )

        validation = run([sys.executable, "scripts/validate_refactor.py"], home, timeout=60)
        write_json(diagnostics / "repository-validation.json", validation)
        doctor_command = [sys.executable, "scripts/doctor.py", "--json"]
        if args.profile:
            doctor_command.extend(("--profile", args.profile))
        doctor = run(doctor_command, home, timeout=30)
        write_json(diagnostics / "doctor.json", doctor)
        write_json(
            diagnostics / "report.json",
            {
                "schema_version": 1,
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "jarvis_release": project_version(),
                "profile": args.profile,
                "privacy": {
                    "raw_audio_included": False,
                    "raw_transcripts_included": False,
                    "clipboard_included": False,
                    "messages_included": False,
                    "logs_included": args.include_logs,
                },
                "host": {
                    "system": platform.system(),
                    "architecture": platform.machine(),
                    "python": platform.python_version(),
                    "desktop_session": os.environ.get("XDG_SESSION_TYPE"),
                },
                "ovos": ovos_versions(home),
                "services": service_state(home),
                "source_inventory": source_inventory,
            },
        )
        if args.include_logs:
            collect_logs(bundle, home)
        write_manifest(bundle)

        with tarfile.open(output, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(
                bundle,
                arcname=bundle.name,
                recursive=True,
                filter=private_tar_info,
            )
    output.chmod(0o600)

    print(f"Created AI support bundle: {output}")
    print("It was not uploaded or shared automatically.")
    if args.include_logs:
        print("Warning: optional logs were included; review the archive before sharing.")
    else:
        print("Raw logs, transcripts, audio, clipboard data and messages were excluded.")
    print(f"Review contents with: tar -tzf {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
